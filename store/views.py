import random
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import (
    Category,
    Course,
    Customer,
    EducationalVideo,
    Order,
    OrderItem,
    PhoneOTP,
    Product,
    SiteSection,
    SiteSettings,
    TeamMember,
)


PROVINCES = [
    'بغداد', 'البصرة', 'نينوى', 'أربيل', 'السليمانية', 'دهوك', 'كركوك',
    'الأنبار', 'ديالى', 'صلاح الدين', 'واسط', 'بابل', 'كربلاء', 'النجف',
    'الديوانية', 'المثنى', 'ذي قار', 'ميسان',
]


def _settings():
    return SiteSettings.load()


def _cart(request):
    return request.session.setdefault('cart', {})


def _cart_count(request):
    cart = request.session.get('cart', {})
    if not cart:
        return 0
    # نتجاهل (وننظّف) أي عنصر لمنتج لم يعد موجوداً حتى لا يعلق العدّاد
    try:
        valid_ids = set(Product.objects.filter(id__in=[int(pid) for pid in cart]).values_list('id', flat=True))
    except (TypeError, ValueError):
        valid_ids = set()
    removed = False
    for pid in list(cart.keys()):
        try:
            exists = int(pid) in valid_ids
        except (TypeError, ValueError):
            exists = False
        if not exists:
            del cart[pid]
            removed = True
    if removed:
        request.session['cart'] = cart
        request.session.modified = True
    return sum(int(item.get('qty', 0)) for item in cart.values())


def _cart_items(request):
    cart = request.session.get('cart', {})
    product_ids = [int(pid) for pid in cart.keys()]
    products = Product.objects.filter(id__in=product_ids)
    products_by_id = {str(p.id): p for p in products}
    items = []
    total = 0
    for pid, data in cart.items():
        product = products_by_id.get(pid)
        if not product:
            continue
        qty = max(1, int(data.get('qty', 1)))
        line_total = float(product.sell_price or 0) * qty
        total += line_total
        items.append({'product': product, 'qty': qty, 'line_total': line_total})
    return items, total


def _base_context(request):
    return {
        'settings': _settings(),
        'cart_count': _cart_count(request),
        'categories': Category.objects.all().order_by('name'),
        'sections': SiteSection.objects.filter(is_active=True),
    }


PER_OPTIONS = [20, 50, 100]


def home(request):
    try:
        per = int(request.GET.get('per', 20))
    except (TypeError, ValueError):
        per = 20
    if per not in PER_OPTIONS:
        per = 20
    search = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'newest')
    products_qs = Product.objects.select_related('category', 'series').all()

    if search:
        products_qs = products_qs.filter(Q(name__icontains=search) | Q(sku__icontains=search) | Q(description__icontains=search))
    if category_id:
        products_qs = products_qs.filter(category_id=category_id)

    if sort == 'price_low':
        products_qs = products_qs.order_by('sell_price')
    elif sort == 'price_high':
        products_qs = products_qs.order_by('-sell_price')
    elif sort == 'best':
        # الأكثر مبيعاً: حسب مجموع الكميات المباعة فعلياً
        products_qs = products_qs.annotate(sold=Sum('orderitem__quantity')).order_by('-sold', '-created_at')
    elif sort == 'popular':
        # الأكثر طلباً: حسب عدد مرات الطلب
        products_qs = products_qs.annotate(order_count=Count('orderitem')).order_by('-order_count', '-created_at')
    elif sort == 'offers':
        products_qs = products_qs.filter(is_offer=True).order_by('-updated_at')
    else:
        products_qs = products_qs.order_by('-created_at')

    context = _base_context(request)
    context.update({
        'products': products_qs[:per],
        'per': per,
        'per_options': PER_OPTIONS,
        # بطاقات العرض في الرئيسية (صور مصغرة)
        'best': list(Product.objects.annotate(sold=Sum('orderitem__quantity')).order_by('-sold', '-created_at')[:4]),
        'popular': list(Product.objects.annotate(order_count=Count('orderitem')).order_by('-order_count', '-created_at')[:4]),
        'offers': list(Product.objects.filter(is_offer=True).order_by('-updated_at')[:4]),
        'newest': list(Product.objects.order_by('-created_at')[:4]),
        # الدورات والفيديوهات لعرضها في الرئيسية (بطاقات عرض + الدورات كمنتجات)
        'home_courses': list(Course.objects.filter(is_active=True).order_by('-created_at')[:8]),
        'home_videos': list(EducationalVideo.objects.filter(is_active=True).order_by('-created_at')[:4]),
        'visited_products': _visited_products(request),
        'search': search,
        'selected_category': category_id,
        'sort': sort,
    })
    return render(request, 'store/home.html', context)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    _remember_product(request, product.id)
    if product.series:
        similar = Product.objects.filter(series=product.series).exclude(pk=product.pk)[:6]
    elif product.category:
        similar = Product.objects.filter(category=product.category).exclude(pk=product.pk)[:6]
    else:
        similar = Product.objects.exclude(pk=product.pk).order_by('-created_at')[:6]
    context = _base_context(request)
    context.update({'product': product, 'similar': similar, 'visited_products': _visited_products(request, exclude_id=product.id)})
    return render(request, 'store/product_detail.html', context)


def _remember_product(request, product_id):
    visited = request.session.get('visited_products', [])
    product_id = int(product_id)
    visited = [pid for pid in visited if pid != product_id]
    visited.insert(0, product_id)
    request.session['visited_products'] = visited[:12]
    request.session.modified = True


def _visited_products(request, exclude_id=None):
    ids = request.session.get('visited_products', [])
    if exclude_id:
        ids = [pid for pid in ids if int(pid) != int(exclude_id)]
    products = Product.objects.filter(id__in=ids)
    by_id = {p.id: p for p in products}
    return [by_id[pid] for pid in ids if pid in by_id][:8]


def courses(request):
    context = _base_context(request)
    context.update({'courses': Course.objects.filter(is_active=True).order_by('-created_at')})
    return render(request, 'store/courses.html', context)


def videos(request):
    context = _base_context(request)
    context.update({'videos': EducationalVideo.objects.filter(is_active=True).order_by('-created_at')})
    return render(request, 'store/videos.html', context)


def about(request):
    context = _base_context(request)
    context.update({'team': TeamMember.objects.filter(is_active=True)})
    return render(request, 'store/about.html', context)


def account(request):
    context = _base_context(request)
    return render(request, 'store/account.html', context)


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk)
    qty = max(1, int(request.POST.get('qty', 1)))
    cart = _cart(request)
    key = str(product.id)
    current = int(cart.get(key, {}).get('qty', 0))
    cart[key] = {'qty': current + qty}
    request.session.modified = True
    # طلب AJAX → نُضيف فقط دون انتقال، ونُعيد عدّاد السلة
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'ok',
            'cart_count': _cart_count(request),
            'product_name': product.name,
        })
    next_url = request.POST.get('next') or 'cart'
    return redirect(next_url)


@require_POST
def cart_update(request, pk):
    cart = _cart(request)
    key = str(pk)
    qty = int(request.POST.get('qty', 1))
    if qty <= 0:
        cart.pop(key, None)
    elif key in cart:
        cart[key] = {'qty': qty}
    request.session.modified = True
    return redirect('cart')


def cart_remove(request, pk):
    cart = _cart(request)
    cart.pop(str(pk), None)
    request.session.modified = True
    return redirect('cart')


def cart_view(request):
    items, total = _cart_items(request)
    context = _base_context(request)
    context.update({'items': items, 'total': total})
    return render(request, 'store/cart.html', context)


def checkout_phone(request):
    items, total = _cart_items(request)
    if not items:
        return redirect('cart')
    context = _base_context(request)
    context.update({'items': items, 'total': total})
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        payment_method = request.POST.get('payment_method', 'cod')
        if phone:
            code = f"{random.randint(100000, 999999)}"
            PhoneOTP.objects.filter(phone=phone, is_used=False).update(is_used=True)
            PhoneOTP.objects.create(phone=phone, code=code)
            request.session['checkout_phone'] = phone
            request.session['payment_method'] = payment_method
            # حل مؤقت: نعرض الرمز على الشاشة فقط عند تفعيل SHOW_OTP (بلا بوابة SMS)
            from django.conf import settings as _s
            request.session['dev_otp_code'] = code if getattr(_s, 'SHOW_OTP', True) else ''
            return redirect('checkout_otp')
        context['error'] = 'اكتب رقم الهاتف.'
    return render(request, 'store/checkout_phone.html', context)


def checkout_otp(request):
    phone = request.session.get('checkout_phone')
    if not phone:
        return redirect('checkout_phone')
    context = _base_context(request)
    context.update({'phone': phone, 'dev_otp_code': request.session.get('dev_otp_code')})
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        otp = PhoneOTP.objects.filter(phone=phone, code=code, is_used=False).order_by('-created_at').first()
        if otp and otp.is_valid():
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            request.session['otp_verified'] = True
            return redirect('checkout_details')
        context['error'] = 'رمز التحقق غير صحيح أو منتهي.'
    return render(request, 'store/checkout_otp.html', context)


def checkout_details(request):
    if not request.session.get('otp_verified'):
        return redirect('checkout_phone')
    items, total = _cart_items(request)
    if not items:
        return redirect('cart')

    phone = request.session.get('checkout_phone')
    customer = Customer.objects.filter(phone=phone).first()
    context = _base_context(request)
    context.update({
        'items': items,
        'total': total,
        'phone': phone,
        'customer': customer,
        'provinces': PROVINCES,
        'payment_method': request.session.get('payment_method', 'cod'),
    })

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        province = request.POST.get('province', '').strip()
        address = request.POST.get('address', '').strip()
        payment_method = request.session.get('payment_method', 'cod')
        if not full_name or not province or not address:
            context['error'] = 'أكمل الاسم والمحافظة والعنوان.'
            return render(request, 'store/checkout_details.html', context)

        user, _ = User.objects.get_or_create(username=phone, defaults={'first_name': full_name})
        customer, _ = Customer.objects.get_or_create(phone=phone, defaults={'user': user})
        customer.user = customer.user or user
        customer.full_name = full_name
        customer.province = province
        customer.address = address
        customer.save()

        order = Order.objects.create(
            customer=customer,
            full_name=full_name,
            phone=phone,
            province=province,
            address=address,
            payment_method=payment_method,
            status='pending',
            total=total,
        )
        for item in items:
            product = item['product']
            OrderItem.objects.create(
                order=order,
                product=product,
                product_sku=product.sku,
                product_name=product.name,
                price=product.sell_price,
                quantity=item['qty'],
                line_total=item['line_total'],
            )

        request.session['cart'] = {}
        request.session['last_order_id'] = order.id
        for key in ('checkout_phone', 'payment_method', 'otp_verified', 'dev_otp_code'):
            request.session.pop(key, None)
        request.session.modified = True

        if payment_method == 'card':
            return redirect('payment_redirect', order_id=order.id)
        return redirect('order_success', order_id=order.id)

    return render(request, 'store/checkout_details.html', context)


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    context = _base_context(request)
    context.update({'order': order})
    return render(request, 'store/order_success.html', context)


def payment_redirect(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    context = _base_context(request)
    context.update({'order': order})
    return render(request, 'store/payment_redirect.html', context)
