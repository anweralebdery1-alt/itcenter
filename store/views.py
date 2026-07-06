import random
import re
import secrets
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.utils import timezone


def _normalize_iraqi_phone(phone):
    """يحوّل الرقم لصيغة otpiq: 964 + الرقم بلا صفر بادئ. مثال 07815453320 -> 9647815453320"""
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('00964'):
        digits = digits[5:]
    elif digits.startswith('964'):
        digits = digits[3:]
    if digits.startswith('0'):
        digits = digits[1:]
    return '964' + digits


def _send_otp_sms(phone, code):
    """يرسل رمز التحقق عبر otpiq. يُرجع (نجاح:bool، تفصيل:str)."""
    if not getattr(settings, 'OTPIQ_API_KEY', ''):
        return False, 'لا يوجد OTPIQ_API_KEY'
    try:
        import requests
        payload = {
            'phoneNumber': _normalize_iraqi_phone(phone),
            'smsType': 'verification',
            'verificationCode': str(code),
            'provider': getattr(settings, 'OTPIQ_PROVIDER', 'sms'),
        }
        sender_id = getattr(settings, 'OTPIQ_SENDER_ID', '')
        if sender_id:
            payload['senderId'] = sender_id
        resp = requests.post(
            getattr(settings, 'OTPIQ_API_URL', 'https://api.otpiq.com/api/sms'),
            headers={
                'Authorization': 'Bearer ' + settings.OTPIQ_API_KEY,
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=getattr(settings, 'OTPIQ_TIMEOUT', 15),
        )
        if 200 <= resp.status_code < 300:
            return True, ''
        detail = f'otpiq {resp.status_code}: {resp.text[:400]}'
        print(detail)
        return False, detail
    except Exception as e:
        detail = f'otpiq خطأ اتصال: {e}'
        print(detail)
        return False, detail


def _valid_iraqi_phone(phone):
    """رقم موبايل عراقي صحيح: بعد المفتاح 964 يكون 10 أرقام تبدأ بـ7."""
    d = re.sub(r'\D', '', phone or '')
    if d.startswith('00964'):
        d = d[5:]
    elif d.startswith('964'):
        d = d[3:]
    if d.startswith('0'):
        d = d[1:]
    return len(d) == 10 and d[0] == '7'


def _phone_display(norm):
    """9647815453320 -> 07815453320 للعرض."""
    d = re.sub(r'\D', '', norm or '')
    if d.startswith('964'):
        d = d[3:]
    return '0' + d if d else ''


def _start_otp(request, phone, next_target, payment_method=None):
    """ينشئ رمزاً ويرسله ويضبط جلسة OTP. phone بصيغة 964..."""
    code = f"{secrets.randbelow(900000) + 100000:06d}"
    PhoneOTP.objects.filter(phone=phone, is_used=False).update(is_used=True)
    PhoneOTP.objects.create(phone=phone, code=code)
    request.session['otp_phone'] = phone
    request.session['otp_next'] = next_target
    if payment_method is not None:
        request.session['otp_payment'] = payment_method
    sms_sent, detail = _send_otp_sms(phone, code)
    request.session['dev_otp_code'] = code if (settings.SHOW_OTP and not sms_sent) else ''
    request.session['otp_sms_sent'] = sms_sent
    request.session['otp_error'] = '' if sms_sent else detail
    if not sms_sent and not settings.SHOW_OTP:
        PhoneOTP.objects.filter(phone=phone, code=code, is_used=False).update(is_used=True)
    return sms_sent


def _login_customer(request, phone):
    """يحفظ تسجيل دخول الزبون لمدة شهر (لا يحتاج OTP عند كل زيارة)."""
    request.session['customer_phone'] = phone
    request.session.set_expiry(60 * 60 * 24 * 30)  # 30 يوماً


OTP_COOLDOWN = 60        # ثانية بين كل إرسال وآخر
OTP_MAX_PER_HOUR = 3     # أقصى عدد رسائل في الساعة


def _otp_wait_seconds(phone):
    """الثواني الواجب انتظارها قبل السماح بإرسال جديد (0 = مسموح الآن)."""
    now = timezone.now()
    last = PhoneOTP.objects.filter(phone=phone).order_by('-created_at').first()
    cooldown = 0
    if last:
        elapsed = (now - last.created_at).total_seconds()
        if elapsed < OTP_COOLDOWN:
            cooldown = int(OTP_COOLDOWN - elapsed) + 1
    hourly = 0
    hour_qs = PhoneOTP.objects.filter(phone=phone, created_at__gte=now - timezone.timedelta(hours=1))
    if hour_qs.count() >= OTP_MAX_PER_HOUR:
        oldest = hour_qs.order_by('created_at').first()
        if oldest:
            hourly = int(3600 - (now - oldest.created_at).total_seconds()) + 1
    return max(0, cooldown, hourly)
from django.db.models import Avg, Count, F, Prefetch, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
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
    Review,
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
    product_ids = []
    for pid in cart.keys():
        try:
            product_ids.append(int(pid))
        except (TypeError, ValueError):
            continue
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
        # التصنيفات الرئيسية فقط (مع أبنائها) لعرضها في شريط التصنيفات
        'categories': (
            Category.objects
            .filter(parent__isnull=True, is_active=True)
            .order_by('order', 'name')
            .prefetch_related(
                Prefetch('children', queryset=Category.objects.filter(is_active=True).order_by('order', 'name'))
            )
        ),
        'sections': SiteSection.objects.filter(is_active=True),
    }


PER_OPTIONS = [20, 50, 100]


def _smart_ordered_products(qs, per):
    """المميّزة أولاً (حسب الأولوية)، ثم البقية: 80% حسب الشعبية (مبيعات + مشاهدات) و20% عشوائي."""
    items = list(qs.annotate(sold=Sum('orderitem__quantity')))
    featured = sorted(
        (p for p in items if p.is_featured),
        key=lambda p: (-p.featured_priority, -(p.created_at.timestamp() if p.created_at else 0)),
    )
    rest = [p for p in items if not p.is_featured]
    max_pop = max(((p.sold or 0) + p.views_count for p in rest), default=0) or 1
    rest.sort(key=lambda p: -(0.8 * (((p.sold or 0) + p.views_count) / max_pop) + 0.2 * random.random()))
    return (featured + rest)[:per]


def home(request):
    try:
        per = int(request.GET.get('per', 20))
    except (TypeError, ValueError):
        per = 20
    if per not in PER_OPTIONS:
        per = 20
    search = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'featured')
    products_qs = Product.objects.select_related('category', 'series').all()

    if search:
        products_qs = products_qs.filter(Q(name__icontains=search) | Q(sku__icontains=search) | Q(description__icontains=search))
    if category_id:
        # عند اختيار تصنيف رئيسي نعرض منتجاته ومنتجات تصنيفاته الفرعية أيضاً
        selected_cat = Category.objects.filter(id=category_id).first()
        if selected_cat:
            child_ids = list(selected_cat.children.values_list('id', flat=True))
            products_qs = products_qs.filter(category_id__in=[selected_cat.id] + child_ids)
        else:
            products_qs = products_qs.filter(category_id=category_id)

    if sort == 'price_low':
        products = list(products_qs.order_by('sell_price')[:per])
    elif sort == 'price_high':
        products = list(products_qs.order_by('-sell_price')[:per])
    elif sort == 'best':
        products = list(products_qs.annotate(sold=Sum('orderitem__quantity')).order_by('-sold', '-created_at')[:per])
    elif sort == 'popular':
        products = list(products_qs.annotate(order_count=Count('orderitem')).order_by('-order_count', '-created_at')[:per])
    elif sort == 'offers':
        products = list(products_qs.filter(is_offer=True).order_by('-updated_at')[:per])
    elif sort == 'newest':
        products = list(products_qs.order_by('-created_at')[:per])
    else:
        # الافتراضي: ترتيب ذكي (مميّزة + 80% شعبية + 20% عشوائي)
        products = _smart_ordered_products(products_qs, per)

    context = _base_context(request)
    context.update({
        'products': products,
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
    product = get_object_or_404(
        Product.objects.prefetch_related('gallery_images'),
        pk=pk,
    )
    _remember_product(request, product.id)
    Product.objects.filter(pk=product.pk).update(views_count=F('views_count') + 1)
    if product.series:
        similar = Product.objects.filter(series=product.series).exclude(pk=product.pk)[:6]
    elif product.category:
        similar = Product.objects.filter(category=product.category).exclude(pk=product.pk)[:6]
    else:
        similar = Product.objects.exclude(pk=product.pk).order_by('-created_at')[:6]
    reviews = product.reviews.filter(is_approved=True)
    stats = reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    context = _base_context(request)
    context.update({
        'product': product,
        'gallery_images': list(product.gallery_images.all()),
        'similar': similar,
        'visited_products': _visited_products(request, exclude_id=product.id),
        'reviews': reviews,
        'review_avg': round(stats['avg'] or 0, 1),
        'review_avg_int': int(round(stats['avg'] or 0)),
        'review_count': stats['count'],
        'review_ok': request.GET.get('review') == 'ok',
    })
    return render(request, 'store/product_detail.html', context)


@require_POST
def submit_review(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = (request.POST.get('name') or '').strip()[:120]
    comment = (request.POST.get('comment') or '').strip()[:2000]
    try:
        rating = int(request.POST.get('rating', 5))
    except (TypeError, ValueError):
        rating = 5
    rating = max(1, min(5, rating))
    if name:
        Review.objects.create(product=product, name=name, rating=rating, comment=comment)
    return redirect(product.get_absolute_url() + '?review=ok#reviews')


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


def robots_txt(request):
    from django.http import HttpResponse
    sitemap_url = request.build_absolute_uri('/sitemap.xml')
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /admin/',
        'Disallow: /account/',
        'Disallow: /cart/',
        'Disallow: /checkout/',
        'Disallow: /api/',
        f'Sitemap: {sitemap_url}',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


def install_app(request):
    """صفحة تعليمات تثبيت المتجر كتطبيق (Add to Home Screen) لكل نظام."""
    context = _base_context(request)
    return render(request, 'store/install.html', context)


def manifest(request):
    """ملف Web App Manifest ليصبح الموقع قابلاً للتثبيت كتطبيق."""
    site = _settings()
    name = site.site_name if site else 'متجر المركز'
    theme = (site.primary_color if site else '') or '#0B4EA2'
    icons = []
    if site and site.logo:
        icon_url = request.build_absolute_uri(site.logo.url)
        for size in ('192x192', '512x512'):
            icons.append({'src': icon_url, 'sizes': size, 'type': 'image/png', 'purpose': 'any'})
    data = {
        'name': name,
        'short_name': name[:12],
        'start_url': '/',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'portrait',
        'background_color': '#ffffff',
        'theme_color': theme,
        'lang': 'ar',
        'dir': 'rtl',
        'icons': icons,
    }
    return JsonResponse(data, content_type='application/manifest+json')


def service_worker(request):
    """Service Worker: تصفّح أسرع + عمل جزئي بلا إنترنت + تحديث تلقائي للمحتوى."""
    js = r"""
const CACHE = 'itc-cache-v1';
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil((async function () {
    const keys = await caches.keys();
    await Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', function (e) {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  // صفحات HTML: الشبكة أولاً ليظهر آخر تحديث دائماً عند توفّر الإنترنت
  if (req.mode === 'navigate') {
    e.respondWith((async function () {
      try {
        const fresh = await fetch(req);
        const cache = await caches.open(CACHE);
        cache.put(req, fresh.clone());
        return fresh;
      } catch (err) {
        return (await caches.match(req)) || (await caches.match('/'));
      }
    })());
    return;
  }
  // الأصول الثابتة والصور: الكاش أولاً لتسريع الزيارات المتكررة
  if (/\.(css|js|png|jpg|jpeg|webp|svg|gif|ico|woff2?)$/i.test(url.pathname) ||
      url.pathname.indexOf('/static/') === 0 || url.pathname.indexOf('/media/') === 0) {
    e.respondWith((async function () {
      const cached = await caches.match(req);
      if (cached) return cached;
      try {
        const fresh = await fetch(req);
        const cache = await caches.open(CACHE);
        cache.put(req, fresh.clone());
        return fresh;
      } catch (err) { return cached; }
    })());
  }
});
"""
    return HttpResponse(js, content_type='application/javascript')


@ensure_csrf_cookie
def account(request):
    context = _base_context(request)
    phone = request.session.get('customer_phone')
    if phone:
        customer = Customer.objects.filter(phone=phone).first()
        orders = Order.objects.filter(phone=phone).order_by('-created_at')[:20]
        context.update({
            'logged_in': True,
            'phone_display': _phone_display(phone),
            'customer': customer,
            'orders': orders,
        })
        return render(request, 'store/account.html', context)

    if request.method == 'POST':
        raw = request.POST.get('phone', '').strip()
        if not _valid_iraqi_phone(raw):
            context['error'] = 'أدخل رقم هاتف عراقي صحيح (10 أرقام تبدأ بـ7).'
        else:
            phone = _normalize_iraqi_phone(raw)
            wait = _otp_wait_seconds(phone)
            if wait > 0:
                context['error'] = f'لقد طلبت رمزاً مؤخراً. حاول بعد {wait} ثانية (بحد أقصى 3 رسائل في الساعة).'
            else:
                sms_sent = _start_otp(request, phone, 'account')
                if not sms_sent and not settings.SHOW_OTP:
                    context['error'] = 'تعذر إرسال رمز التحقق حاليا. تأكد من إعدادات OTPIQ ثم حاول مرة أخرى.'
                else:
                    return redirect('checkout_otp')
        context['form_phone'] = raw
    context['logged_in'] = False
    return render(request, 'store/account.html', context)


@ensure_csrf_cookie
def account_details(request):
    phone = request.session.get('customer_phone')
    if not phone:
        return redirect('account')

    user, _ = User.objects.get_or_create(username=phone)
    customer, _ = Customer.objects.get_or_create(phone=phone, defaults={'user': user})
    if not customer.user:
        customer.user = user
        customer.save(update_fields=['user'])

    context = _base_context(request)
    context.update({
        'customer': customer,
        'phone_display': _phone_display(phone),
        'provinces': PROVINCES,
    })

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        province = request.POST.get('province', '').strip()
        address = request.POST.get('address', '').strip()
        if len(full_name.split()) < 3:
            context['error'] = 'اكتب اسمك الثلاثي كاملاً.'
        elif not province or not address:
            context['error'] = 'أكمل المحافظة والعنوان.'
        else:
            user.first_name = full_name
            user.save(update_fields=['first_name'])
            customer.full_name = full_name
            customer.province = province
            customer.address = address
            customer.save()
            return redirect(request.POST.get('next') or 'account')

    return render(request, 'store/account_details.html', context)


def account_logout(request):
    for k in ('customer_phone', 'otp_phone', 'otp_next', 'otp_payment', 'otp_full_name',
              'otp_verified', 'dev_otp_code', 'otp_sms_sent'):
        request.session.pop(k, None)
    request.session.modified = True
    return redirect('account')


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
    try:
        qty = int(request.POST.get('qty', 1))
    except (TypeError, ValueError):
        qty = 1
    if qty <= 0:
        cart.pop(key, None)
    elif key in cart:
        cart[key] = {'qty': qty}
    request.session.modified = True
    return redirect('cart')


@require_POST
def cart_remove(request, pk):
    cart = _cart(request)
    cart.pop(str(pk), None)
    request.session.modified = True
    return redirect('cart')


@ensure_csrf_cookie
def cart_view(request):
    items, total = _cart_items(request)
    context = _base_context(request)
    context.update({'items': items, 'total': total})
    return render(request, 'store/cart.html', context)


@ensure_csrf_cookie
def checkout_phone(request):
    items, total = _cart_items(request)
    if not items:
        return redirect('cart')
    context = _base_context(request)
    logged_phone = request.session.get('customer_phone')
    context.update({'items': items, 'total': total, 'logged_phone': logged_phone,
                    'logged_phone_display': _phone_display(logged_phone) if logged_phone else ''})
    if request.method == 'POST':
        raw = request.POST.get('phone', '').strip()
        payment_method = request.POST.get('payment_method', 'cod')
        if not _valid_iraqi_phone(raw):
            context['error'] = 'أدخل رقم هاتف عراقي صحيح (10 أرقام تبدأ بـ7).'
            return render(request, 'store/checkout_phone.html', context)
        phone = _normalize_iraqi_phone(raw)
        request.session['otp_payment'] = payment_method
        # مسجّل خلال شهر بنفس الرقم؟ تجاوز OTP مباشرة
        if logged_phone and logged_phone == phone:
            request.session['otp_phone'] = phone
            request.session['otp_verified'] = True
            return redirect('checkout_details')
        wait = _otp_wait_seconds(phone)
        if wait > 0:
            context['error'] = f'لقد طلبت رمزاً مؤخراً. حاول بعد {wait} ثانية (بحد أقصى 3 رسائل في الساعة).'
            return render(request, 'store/checkout_phone.html', context)
        sms_sent = _start_otp(request, phone, 'checkout', payment_method)
        if not sms_sent and not settings.SHOW_OTP:
            context['error'] = 'تعذر إرسال رمز التحقق حاليا. تأكد من إعدادات OTPIQ ثم حاول مرة أخرى.'
            return render(request, 'store/checkout_phone.html', context)
        return redirect('checkout_otp')
    return render(request, 'store/checkout_phone.html', context)


@ensure_csrf_cookie
def checkout_otp(request):
    phone = request.session.get('otp_phone')
    if not phone:
        return redirect('account')
    context = _base_context(request)
    context.update({
        'phone': _phone_display(phone),
        'dev_otp_code': request.session.get('dev_otp_code'),
        'otp_sms_sent': request.session.get('otp_sms_sent', False),
        'otp_error': request.session.get('otp_error', '') if settings.DEBUG or settings.SHOW_OTP else '',
        'resend_after': _otp_wait_seconds(phone),
    })
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        otp = PhoneOTP.objects.filter(phone=phone, code=code, is_used=False).order_by('-created_at').first()
        if otp and otp.is_valid():
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            _login_customer(request, phone)   # تسجيل دخول لمدة شهر
            if request.session.get('otp_next') == 'checkout':
                request.session['otp_verified'] = True
                return redirect('checkout_details')
            cust, _ = Customer.objects.get_or_create(phone=phone)
            return redirect('account_details')
        context['error'] = 'رمز التحقق غير صحيح أو منتهي.'
    return render(request, 'store/checkout_otp.html', context)


@require_POST
def resend_otp(request):
    phone = request.session.get('otp_phone')
    if not phone:
        return redirect('account')
    if _otp_wait_seconds(phone) <= 0:
        _start_otp(request, phone, request.session.get('otp_next', 'account'),
                   request.session.get('otp_payment'))
    return redirect('checkout_otp')


@ensure_csrf_cookie
def checkout_details(request):
    if not request.session.get('otp_verified'):
        return redirect('checkout_phone')
    items, total = _cart_items(request)
    if not items:
        return redirect('cart')

    phone = request.session.get('otp_phone')
    customer = Customer.objects.filter(phone=phone).first()
    profile_complete = bool(customer and customer.full_name and customer.province and customer.address)
    editing_address = request.GET.get('edit') == '1' or not profile_complete
    context = _base_context(request)
    context.update({
        'items': items,
        'total': total,
        'phone': _phone_display(phone),
        'customer': customer,
        'provinces': PROVINCES,
        'payment_method': request.session.get('otp_payment', 'cod'),
        'profile_complete': profile_complete,
        'editing_address': editing_address,
    })

    if request.method == 'POST':
        full_name = (request.POST.get('full_name') or (customer.full_name if customer else '')).strip()
        province = (request.POST.get('province') or (customer.province if customer else '')).strip()
        address = (request.POST.get('address') or (customer.address if customer else '')).strip()
        payment_method = request.session.get('otp_payment', 'cod')
        if len(full_name.split()) < 3 or not province or not address:
            context['error'] = 'أكمل الاسم الثلاثي والمحافظة والعنوان.'
            context['editing_address'] = True
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
        # ننظّف مفاتيح OTP المؤقتة فقط؛ نُبقي customer_phone (تسجيل الدخول لشهر)
        for key in ('otp_phone', 'otp_payment', 'otp_next', 'otp_verified', 'dev_otp_code', 'otp_sms_sent'):
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
