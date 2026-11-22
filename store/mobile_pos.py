# -*- coding: utf-8 -*-
"""البيع من الهاتف (/pos/): بيع ووصل، الوصولات، والمشاريع.

لا جداول جديدة للوصولات والمشاريع على السيرفر: الهاتف يكتب أحداثاً بنفس صيغة
برنامج الأوفلاين تماماً (sale · stock_move · project · project_payment) في
PosEvent، فتسحبها الحاسبتان وتطبّقها كأنها من جهاز ثالث. والقراءة كذلك تُبنى
من السجل نفسه — هو مصدر الحقيقة الكامل للنظام.
"""

import json
import uuid as uuid_module
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import MobilePosProfile, PosDevice, PosEvent, Product, SiteSettings
from .pos_sync import _materialize

LOGIN_URL = '/admin/login/'

# نفس حقول المشروع في البرنامج (db_core.PROJECT_FIELDS)
PROJECT_FIELDS = (
    'name', 'person', 'phone', 'practical_details', 'practical_price',
    'materials_cost', 'theory_details', 'theory_price', 'theory_owner',
    'theory_share_pct', 'note', 'status', 'year', 'archived_at',
    'duration',          # مدة الإنجاز — البرنامج v1.9.1
)
PROJECT_MONEY_FIELDS = ('practical_price', 'materials_cost', 'theory_price', 'theory_share_pct')
PAYMENT_KINDS = ('client', 'theory_payout')


# ---------------------------------------------------------------- أدوات

def _utc_now_iso():
    """نفس طابع البرنامج: 2026-08-10T12:34:56.789Z"""
    return timezone.now().isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def _new_uuid():
    return str(uuid_module.uuid4())


def _clean_phone(phone):
    """نفس توحيد البرنامج: أرقام فقط بصيغة 07XXXXXXXXX."""
    digits = ''.join(ch for ch in str(phone or '') if ch.isdigit())
    if digits.startswith('00964'):
        digits = '0' + digits[5:]
    elif digits.startswith('964'):
        digits = '0' + digits[3:]
    return digits[:15]


def _num(value, default=0.0):
    try:
        return float(str(value).replace(',', '').strip() or default)
    except (TypeError, ValueError):
        return default


def _money(value):
    """نفس صيغة وصل البرنامج: 10,000.00"""
    return f'{_num(value):,.2f}'


def _sale_date(value):
    """تاريخ الوصل بصيغة البرنامج «2026-11-21 15:04». يُقبل من الهاتف (قابل للتعديل
    كما في نافذة الوصل في البرنامج) وإلا فالآن بتوقيت بغداد."""
    from datetime import datetime
    text = str(value or '').strip().replace('T', ' ')[:16]
    try:
        return datetime.strptime(text, '%Y-%m-%d %H:%M').strftime('%Y-%m-%d %H:%M')
    except ValueError:
        return timezone.localtime().strftime('%Y-%m-%d %H:%M')


def _profile(request):
    profile = MobilePosProfile.objects.filter(user=request.user, is_active=True).first()
    return profile


def _profile_required(view):
    """دخول بحساب لوحة الإدارة + حساب بيع بالهاتف مفعّل."""
    @login_required(login_url=LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        profile = _profile(request)
        if not profile:
            if request.path.startswith('/pos/api/'):
                return JsonResponse({'ok': False, 'error': 'لا يوجد حساب بيع بالهاتف لهذا المستخدم'},
                                    status=403)
            return HttpResponseForbidden(
                'لا يوجد حساب بيع بالهاتف لهذا المستخدم. أضفه من لوحة الإدارة ← حسابات البيع بالهاتف.')
        request.pos_profile = profile
        return view(request, *args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper


def _body(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return {}


def _emit(profile, entity, entity_uuid, op, payload, now):
    """يسجّل حدثاً كأنه من جهاز البرنامج، ويطبّق أثره على المتجر (المخزون)."""
    event = PosEvent.objects.create(
        uuid=_new_uuid(), entity=entity, entity_uuid=entity_uuid, op=op,
        payload=payload, device_id=profile.device_id,
        user_name=profile.pos_username, created_at=now)
    _materialize(event)
    return event


# ---------------------------------------------------------------- بناء الحالة من السجل

def _sales_state():
    """الوصولات كما تراها الحاسبتان: آخر نسخة لكل وصل، مع الحذف."""
    sales = {}
    deleted = set()
    for entity_uuid, op, payload, user_name, device_id in (
            PosEvent.objects.filter(entity='sale').order_by('seq')
            .values_list('entity_uuid', 'op', 'payload', 'user_name', 'device_id')):
        payload = payload or {}
        key = payload.get('uuid') or entity_uuid
        if not key:
            continue
        if op == 'delete':
            deleted.add(key)
            continue
        current = sales.get(key)
        if current and not payload.get('items'):
            current.update({k: v for k, v in payload.items() if k != 'items'})
        else:
            first = ({'_seller': current['_seller'], '_device': current['_device']} if current
                     else {'_seller': user_name or '', '_device': device_id or ''})
            sales[key] = dict(payload, **first)
    return {k: v for k, v in sales.items() if k not in deleted}


def _device_names():
    """اسم مقروء لكل جهاز: الحاسبات من «أجهزة نقاط البيع»، والهواتف من حساباتها."""
    names = dict(PosDevice.objects.values_list('device_id', 'name'))
    names.update({p.device_id: f'هاتف {p.pos_username}' for p in MobilePosProfile.objects.all()})
    names['website'] = 'الموقع'
    return names


def _seller_label(sale, names):
    """«انور · هاتف انور»: البائع (مستخدم البرنامج) والجهاز الذي صدر منه الوصل."""
    seller = sale.get('_seller') or ''
    device = names.get(sale.get('_device') or '', '')
    return ' · '.join(x for x in (seller, device) if x) or '—'


def _projects_state():
    """المشاريع ودفعاتها: الأحدث (updated_at) يفوز، والحذف منطقي — كالبرنامج."""
    projects, payments = {}, {}
    for entity, op, payload in (PosEvent.objects.filter(entity__in=('project', 'project_payment'))
                                .order_by('seq').values_list('entity', 'op', 'payload')):
        payload = payload or {}
        row_uuid = payload.get('uuid')
        if not row_uuid:
            continue
        if entity == 'project':
            if op == 'delete':
                if row_uuid in projects:
                    projects[row_uuid]['deleted_at'] = payload.get('deleted_at') or 'x'
                continue
            current = projects.get(row_uuid)
            # الأحداث مرتّبة بالتسلسل: عند تساوي الطابع (تعديلان في نفس الجزء من الثانية) يفوز الأحدث
            if current and str(payload.get('updated_at') or '') < str(current.get('updated_at') or ''):
                continue
            projects[row_uuid] = dict(payload)
        else:
            if op == 'delete':
                if row_uuid in payments:
                    payments[row_uuid]['deleted_at'] = payload.get('deleted_at') or 'x'
                continue
            payments.setdefault(row_uuid, dict(payload))
    return projects, payments


def _project_financials(row, paid_client=0.0, paid_theory=0.0):
    """نسخة من db_core.project_financials — مصدر الحساب نفسه."""
    practical_price = _num(row.get('practical_price'))
    materials_cost = _num(row.get('materials_cost'))
    theory_price = _num(row.get('theory_price'))
    share_pct = row.get('theory_share_pct')
    share_pct = 80.0 if share_pct in (None, '') else _num(share_pct, 80.0)
    total_fees = practical_price + theory_price
    theory_owner_share = theory_price * share_pct / 100.0
    our_theory_share = theory_price - theory_owner_share
    return {
        'total_fees': total_fees,
        'practical_profit': practical_price - materials_cost,
        'theory_owner_share': theory_owner_share,
        'our_theory_share': our_theory_share,
        'our_income': practical_price - materials_cost + our_theory_share,
        'client_remaining': total_fees - paid_client,
        'theory_owner_remaining': theory_owner_share - paid_theory,
        'paid_client': paid_client,
        'paid_theory': paid_theory,
    }


# ---------------------------------------------------------------- الصفحات

@_profile_required
def pos_home(request):
    profile = request.pos_profile
    return render(request, 'store/mobile_pos.html', {
        'profile': profile,
        'today': date.today().isoformat(),
        'next_receipt': f'{profile.receipt_prefix}-{profile.last_receipt_no + 1}',
    })


@_profile_required
def pos_receipt(request, sale_uuid):
    sale = _sales_state().get(str(sale_uuid))
    if not sale:
        raise Http404('الوصل غير موجود')
    items = []
    for item in sale.get('items') or []:
        price = _num(item.get('price'))
        qty = int(_num(item.get('quantity')))
        items.append({'name': item.get('name') or '', 'qty': qty,
                      'price_s': _money(price), 'total_s': _money(price * qty)})
    total = _num(sale.get('total'))
    discount = _num(sale.get('discount'))
    net = total - discount
    site = SiteSettings.load()
    phone = str(sale.get('phone') or '')
    lines = [f"وصل رقم {sale.get('receipt_no')} — مركز آي تي للتطوير والتدريب", str(sale.get('date') or '')]
    lines += [f"• {i['name']} × {i['qty']} = {i['total_s']}" for i in items]
    if discount:
        lines.append(f'الخصم: {_money(discount)} د.ع')
    lines.append(f'الصافي: {_money(net)} د.ع')
    lines.append('شكراً لتعاملكم معنا')
    return render(request, 'store/mobile_receipt.html', {
        'sale': sale, 'items': items, 'total_s': _money(total), 'discount_s': _money(discount),
        'net_s': _money(net),
        'logo_url': site.logo.url if getattr(site, 'logo', None) else '',
        'wa_phone': ('964' + phone[1:]) if phone.startswith('07') else '',
        'seller': _seller_label(sale, _device_names()),
        'wa_text': '\n'.join(lines),
    })


# ---------------------------------------------------------------- واجهات البيانات

@require_GET
@_profile_required
def api_products(request):
    """كل منتجات البرنامج — الظاهرة في الموقع والمخفية — عدا المحذوفة."""
    rows = []
    for p in Product.objects.filter(deleted_at__isnull=True).only(
            'uuid', 'name', 'sku', 'sell_price', 'quantity', 'image'):
        rows.append({
            'u': str(p.uuid), 'n': p.name, 's': p.sku or '',
            'p': float(p.sell_price or 0), 'q': int(p.quantity or 0),
            'i': p.image.url if p.image else '',
        })
    return JsonResponse({'ok': True, 'products': rows})


@require_POST
@_profile_required
def api_sale(request):
    """بيعة كاملة بنفس منطق db_core.record_sale: وصل + عناصره + حركات مخزون."""
    profile = request.pos_profile
    data = _body(request)
    buyer = str(data.get('buyer') or '').strip()[:200]
    phone = _clean_phone(data.get('phone'))
    discount = max(0.0, _num(data.get('discount')))
    sale_date = _sale_date(data.get('date'))
    lines = data.get('items') or []
    if not lines:
        return JsonResponse({'ok': False, 'error': 'السلة فارغة'}, status=400)

    wanted = {}
    for line in lines:
        product_uuid = str(line.get('u') or '')
        qty = int(_num(line.get('q')))
        if not product_uuid or qty <= 0:
            return JsonResponse({'ok': False, 'error': 'كمية غير صحيحة'}, status=400)
        entry = wanted.setdefault(product_uuid, {'qty': 0, 'price': _num(line.get('p'))})
        entry['qty'] += qty

    with transaction.atomic():
        profile = MobilePosProfile.objects.select_for_update().get(pk=profile.pk)
        products = {str(p.uuid): p for p in Product.objects.select_for_update().filter(
            uuid__in=list(wanted), deleted_at__isnull=True)}
        for product_uuid, entry in wanted.items():
            product = products.get(product_uuid)
            if not product:
                return JsonResponse({'ok': False, 'error': 'منتج غير موجود (ربما حُذف)'}, status=400)
            if int(product.quantity or 0) < entry['qty']:
                return JsonResponse({'ok': False, 'error':
                                     f'الكمية المتوفرة للمنتج {product.name} أقل من المطلوب '
                                     f'(المتوفر {int(product.quantity or 0)})'}, status=400)
            if entry['price'] < 0:
                return JsonResponse({'ok': False, 'error': 'سعر غير صحيح'}, status=400)

        profile.last_receipt_no += 1
        profile.save(update_fields=['last_receipt_no'])
        receipt_no = f'{profile.receipt_prefix}-{profile.last_receipt_no}'

        now = _utc_now_iso()
        sale_uuid = _new_uuid()
        total = 0.0
        payload_items = []
        for product_uuid, entry in wanted.items():
            product = products[product_uuid]
            total += entry['price'] * entry['qty']
            payload_items.append({
                'uuid': _new_uuid(), 'product_uuid': product_uuid,
                'sku': product.sku or '', 'name': product.name,
                'price': float(entry['price']), 'quantity': int(entry['qty']),
            })
            move_uuid = _new_uuid()
            _emit(profile, 'stock_move', move_uuid, 'insert', {
                'uuid': move_uuid, 'product_uuid': product_uuid, 'delta': -int(entry['qty']),
                'reason': 'sale', 'ref_type': 'sale', 'ref_uuid': sale_uuid,
                'note': None, 'device_id': profile.device_id, 'created_at': now,
            }, now)

        payload = {
            'uuid': sale_uuid, 'receipt_no': receipt_no, 'buyer': buyer,
            'total': total, 'discount': discount, 'date': sale_date,
            'phone': phone, 'device_id': profile.device_id, 'updated_at': now,
            'items': payload_items,
        }
        _emit(profile, 'sale', sale_uuid, 'insert', payload, now)

    return JsonResponse({'ok': True, 'uuid': sale_uuid, 'receipt_no': receipt_no})


@require_GET
@_profile_required
def api_sales(request):
    """الوصولات (من الحاسبتين والهاتف) — الأحدث أولاً."""
    query = str(request.GET.get('q') or '').strip()
    names = _device_names()
    rows = []
    for sale in _sales_state().values():
        if query:
            haystack = ' '.join([str(sale.get('receipt_no') or ''), str(sale.get('buyer') or ''),
                                 str(sale.get('phone') or '')]
                                + [str(i.get('name') or '') for i in sale.get('items') or []])
            if query.lower() not in haystack.lower():
                continue
        total = _num(sale.get('total'))
        discount = _num(sale.get('discount'))
        rows.append({
            'uuid': sale.get('uuid'), 'no': sale.get('receipt_no') or '',
            'buyer': sale.get('buyer') or '', 'phone': sale.get('phone') or '',
            'date': sale.get('date') or '', 'net': total - discount,
            'count': sum(int(_num(i.get('quantity'))) for i in sale.get('items') or []),
            'online': bool(sale.get('online_order_id')),
            'seller': _seller_label(sale, names),
        })
    rows.sort(key=lambda r: r['date'], reverse=True)
    today = timezone.localtime().strftime('%Y-%m-%d')
    today_total = sum(r['net'] for r in rows if r['date'].startswith(today)) if not query else None
    return JsonResponse({'ok': True, 'sales': rows[:150], 'today_total': today_total})


@require_GET
@_profile_required
def api_projects(request):
    projects, payments = _projects_state()
    paid = {}
    by_project = {}
    for pay in payments.values():
        if pay.get('deleted_at'):
            continue
        key = pay.get('project_uuid')
        sums = paid.setdefault(key, {'client': 0.0, 'theory_payout': 0.0})
        sums[pay.get('kind') if pay.get('kind') in sums else 'client'] += _num(pay.get('amount'))
        by_project.setdefault(key, []).append({
            'kind': pay.get('kind'), 'amount': _num(pay.get('amount')),
            'date': pay.get('date') or '', 'note': pay.get('note') or ''})
    show_archived = request.GET.get('archived') == '1'
    rows = []
    for project_uuid, project in projects.items():
        if project.get('deleted_at'):
            continue
        if project.get('archived_at') and not show_archived:
            continue
        sums = paid.get(project_uuid, {'client': 0.0, 'theory_payout': 0.0})
        row = {k: project.get(k) for k in PROJECT_FIELDS}
        row['uuid'] = project_uuid
        row['created_at'] = project.get('created_at') or ''
        row['fin'] = _project_financials(project, sums['client'], sums['theory_payout'])
        row['payments'] = sorted(by_project.get(project_uuid, []), key=lambda p: p['date'])
        rows.append(row)
    rows.sort(key=lambda r: r['created_at'], reverse=True)
    return JsonResponse({'ok': True, 'projects': rows})


@require_POST
@_profile_required
def api_project_save(request):
    """إضافة مشروع أو تعديله — حدث كامل بنفس payload البرنامج (_project_payload)."""
    profile = request.pos_profile
    data = _body(request)
    name = str(data.get('name') or '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': 'اسم المشروع مطلوب'}, status=400)

    values = {}
    for key in PROJECT_FIELDS:
        if key in ('status', 'year', 'archived_at'):
            continue
        if key in PROJECT_MONEY_FIELDS:
            values[key] = _num(data.get(key))
        else:
            values[key] = str(data.get(key) or '').strip()
    if str(data.get('theory_share_pct') or '').strip() == '':
        values['theory_share_pct'] = 80.0
    values['phone'] = _clean_phone(values['phone']) or values['phone']

    now = _utc_now_iso()
    project_uuid = str(data.get('uuid') or '').strip()
    with transaction.atomic():
        if project_uuid:
            projects, _ = _projects_state()
            existing = projects.get(project_uuid)
            if not existing or existing.get('deleted_at'):
                return JsonResponse({'ok': False, 'error': 'المشروع غير موجود'}, status=404)
            payload = dict(existing)
            payload.update(values)
            payload['updated_at'] = now
            op = 'update'
        else:
            project_uuid = _new_uuid()
            payload = dict(values)
            payload.update({'status': 'open', 'year': date.today().year, 'archived_at': None,
                            'uuid': project_uuid, 'device_id': profile.device_id,
                            'created_at': now, 'updated_at': now, 'deleted_at': None})
            op = 'insert'
        _emit(profile, 'project', project_uuid, op, payload, now)
        first_pay = _num(data.get('first_pay'))
        if op == 'insert' and first_pay > 0:
            # دفعة أولى (عربون) مع الإضافة — كما في نموذج البرنامج
            payment_uuid = _new_uuid()
            _emit(profile, 'project_payment', payment_uuid, 'insert', {
                'project_uuid': project_uuid, 'kind': 'client', 'amount': first_pay,
                'date': date.today().isoformat(), 'note': 'دفعة أولى',
                'uuid': payment_uuid, 'device_id': profile.device_id, 'created_at': now,
            }, now)
    return JsonResponse({'ok': True, 'uuid': project_uuid})


@require_POST
@_profile_required
def api_project_payment(request):
    """دفعة زبون أو تسليم لصاحب النظري — بنفس payload البرنامج."""
    profile = request.pos_profile
    data = _body(request)
    project_uuid = str(data.get('project_uuid') or '').strip()
    kind = str(data.get('kind') or 'client')
    amount = _num(data.get('amount'))
    if kind not in PAYMENT_KINDS or amount <= 0:
        return JsonResponse({'ok': False, 'error': 'المبلغ أو النوع غير صحيح'}, status=400)
    projects, _ = _projects_state()
    project = projects.get(project_uuid)
    if not project or project.get('deleted_at'):
        return JsonResponse({'ok': False, 'error': 'المشروع غير موجود'}, status=404)
    pay_date = str(data.get('date') or '').strip()[:10] or date.today().isoformat()
    now = _utc_now_iso()
    payment_uuid = _new_uuid()
    with transaction.atomic():
        _emit(profile, 'project_payment', payment_uuid, 'insert', {
            'project_uuid': project_uuid, 'kind': kind, 'amount': amount,
            'date': pay_date, 'note': str(data.get('note') or '').strip(),
            'uuid': payment_uuid, 'device_id': profile.device_id, 'created_at': now,
        }, now)
    return JsonResponse({'ok': True, 'uuid': payment_uuid})


def pos_manifest(request):
    """تثبيت صفحة البيع على الشاشة الرئيسية كتطبيق مستقل يفتح على /pos/."""
    site = SiteSettings.load()
    icons = []
    if getattr(site, 'logo', None):
        url = request.build_absolute_uri(site.logo.url)
        icons = [{'src': url, 'sizes': s, 'type': 'image/png', 'purpose': 'any'}
                 for s in ('192x192', '512x512')]
    return JsonResponse({
        'name': 'بيع المحل — مركز آي تي', 'short_name': 'بيع المحل',
        'start_url': '/pos/', 'scope': '/pos/', 'display': 'standalone',
        'orientation': 'portrait', 'background_color': '#ffffff',
        'theme_color': '#0B4EA2', 'lang': 'ar', 'dir': 'rtl', 'icons': icons,
    }, content_type='application/manifest+json')
