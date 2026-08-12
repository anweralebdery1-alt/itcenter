# -*- coding: utf-8 -*-
"""مزامنة نقاط البيع مع الموقع.

الموقع هو نقطة الالتقاء بين الحاسبتين: كل حاسبة ترفع ما عندها من أحداث،
وتسحب ما رفعته الأخرى. الأحداث تُخزَّن كما هي في PosEvent (وهي السجل الكامل
للنظام)، ثم يُطبَّق منها على المتجر ما يهمّ الزبون: المنتجات وحركات المخزون.

قواعد ثابتة:
- كل حدث له uuid فريد → إعادة إرساله لا تُكرّر أثره (مهم مع إنترنت متقطّع).
- المنتجات تُطابق بالـuuid حصراً، لا بالـSKU (الـSKU يجوز تكراره).
- لا حذف فيزيائي: نضع deleted_at.
- الكمية = مجموع الحركات، تُحسب ولا تُكتب.
"""

import json
import logging
import secrets

from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import AppRelease, PosDevice, PosEvent, Product, StockMove


logger = logging.getLogger(__name__)

MAX_PULL_LIMIT = 500
MAX_PUSH_EVENTS = 1000
SUPPORTED_ENTITIES = {
    'product', 'stock_move', 'sale', 'withdrawal',
    'salary', 'expense', 'transfer', 'user',
}


# ---------------------------------------------------------------- المصادقة

def _bearer_token(request):
    header = request.headers.get('Authorization', '')
    parts = header.split()
    if len(parts) == 2 and parts[0].lower() in {'token', 'bearer'}:
        return parts[1]
    return parts[-1] if parts else ''


def _authenticate(request):
    """يُرجع (device, error_response). لكل حاسبة رمزها الخاص فيمكن إيقاف واحدة وحدها."""
    token = _bearer_token(request)
    if not token:
        return None, JsonResponse({'status': 'error', 'error': 'missing token'}, status=401)

    for device in PosDevice.objects.filter(is_active=True):
        if secrets.compare_digest(device.token, token):
            return device, None
    return None, JsonResponse({'status': 'error', 'error': 'invalid token'}, status=401)


def _touch(device):
    PosDevice.objects.filter(pk=device.pk).update(last_seen=timezone.now())


# ---------------------------------------------------------------- تطبيق الأحداث

def _parse_ts(value):
    """يحوّل الطابع الزمني القادم من الحاسبة إلى نص قابل للمقارنة، أو '' إن كان فارغاً."""
    return str(value or '').strip()


def _apply_product(payload):
    """إنشاء/تحديث منتج. عند التعارض يفوز الأحدث حسب طابع نقطة البيع.
    ملاحظة: الكمية ليست هنا عمداً — المخزون يصل عبر الحركات فقط."""
    product_uuid = payload.get('uuid')
    if not product_uuid:
        return 'skipped: missing uuid'

    incoming_ts = _parse_ts(payload.get('updated_at'))
    product = Product.objects.filter(uuid=product_uuid).first()

    if product is None:
        product = _adopt_legacy_product(payload, product_uuid)

    if product and product.pos_updated_at and incoming_ts:
        if incoming_ts < product.pos_updated_at:
            return 'ignored: older than stored version'

    fields = {
        'name': str(payload.get('name') or 'بلا اسم')[:300],
        'sku': str(payload.get('sku') or '')[:100],
        'pos_updated_at': incoming_ts,
    }
    for source, target in (('buy_price', 'buy_price'), ('sell_price', 'sell_price')):
        try:
            fields[target] = float(payload.get(source) or 0)
        except (TypeError, ValueError):
            fields[target] = 0.0

    if payload.get('deleted_at'):
        fields['deleted_at'] = timezone.now()

    if product:
        for key, value in fields.items():
            setattr(product, key, value)
        # لا نلمس الوصف والصورة والتصنيف — هذه يديرها المالك من لوحة الإدارة
        product.save(update_fields=list(fields.keys()))
        return 'updated'

    Product.objects.create(uuid=product_uuid, quantity=0, **fields)
    return 'created'


def _adopt_legacy_product(payload, product_uuid):
    """يتبنّى منتجاً قديماً بدل إنشاء نسخة ثانية منه.

    المزامنة القديمة كانت تطابق بـlocal_id، والحديثة تطابق بـuuid. فمنتج
    وصل قديماً ثم عاد بمعرّف جديد كان يُنشئ صفاً ثانياً — ويضيع معه ما أضافه
    المالك من صورة ووصف وتصنيف.

    نتبنّاه بشرطين معاً حتى لا نخلط بين منتجين:
    - مطابقة تامة للاسم والـSKU.
    - وجود مرشّح واحد فقط لم تلمسه المزامنة الحديثة من قبل.
    """
    name = str(payload.get('name') or '').strip()
    sku = str(payload.get('sku') or '').strip()
    if not name:
        return None

    candidates = list(Product.objects.filter(
        name=name, sku=sku, deleted_at__isnull=True, pos_updated_at=''
    )[:2])
    if len(candidates) != 1:
        return None          # صفر أو أكثر من واحد → لا نخمّن

    adopted = candidates[0]
    adopted.uuid = product_uuid
    adopted.save(update_fields=['uuid'])
    logger.info('adopted legacy product %s as %s', adopted.pk, product_uuid)
    return adopted


def _apply_product_delete(payload):
    product_uuid = payload.get('uuid')
    if not product_uuid:
        return 'skipped: missing uuid'
    # الحذف بالـuuid فقط — منتج آخر بنفس الـSKU لا يتأثر إطلاقاً
    updated = Product.objects.filter(uuid=product_uuid, deleted_at__isnull=True).update(
        deleted_at=timezone.now())
    return 'deleted' if updated else 'already deleted'


def _apply_stock_move(payload):
    move_uuid = payload.get('uuid')
    product_uuid = payload.get('product_uuid')
    if not move_uuid or not product_uuid:
        return 'skipped: missing uuid'
    if StockMove.objects.filter(uuid=move_uuid).exists():
        return 'duplicate'

    try:
        delta = int(payload.get('delta') or 0)
    except (TypeError, ValueError):
        return 'skipped: bad delta'

    product = Product.objects.filter(uuid=product_uuid).first()
    StockMove.objects.create(
        uuid=move_uuid,
        product=product,
        product_uuid=product_uuid,
        delta=delta,
        reason=str(payload.get('reason') or 'adjust')[:30],
        ref_type=str(payload.get('ref_type') or '')[:20],
        ref_uuid=str(payload.get('ref_uuid') or '')[:64],
        note=str(payload.get('note') or '')[:250],
        device_id=str(payload.get('device_id') or '')[:64],
        created_at=_parse_ts(payload.get('created_at')),
    )
    recompute_product_quantity(product_uuid)
    return 'applied'


def recompute_product_quantity(product_uuid):
    """الكمية = مجموع الحركات. المنتجات المضافة من لوحة الإدارة (بلا حركات)
    تُترك بكميتها اليدوية ولا تُصفَّر."""
    product = Product.objects.filter(uuid=product_uuid).first()
    if not product:
        return None
    aggregate = StockMove.objects.filter(product_uuid=product_uuid).aggregate(total=Sum('delta'))
    if aggregate['total'] is None:
        return product.quantity
    Product.objects.filter(pk=product.pk).update(quantity=aggregate['total'])
    return aggregate['total']


def _materialize(event):
    """يطبّق الحدث على بيانات المتجر. الكيانات غير المذكورة تُخزَّن وتُمرَّر
    للحاسبة الأخرى فقط (المبيعات والحركات المالية شأن داخلي بين الحاسبتين)."""
    if event.entity == 'product':
        if event.op == 'delete':
            return _apply_product_delete(event.payload)
        return _apply_product(event.payload)
    if event.entity == 'stock_move' and event.op == 'insert':
        return _apply_stock_move(event.payload)
    return 'relayed'


# ---------------------------------------------------------------- نقاط الاتصال

@csrf_exempt
@require_POST
def pos_push(request):
    """ترفع الحاسبة ما لديها من أحداث. مكرّر الإرسال آمن تماماً."""
    device, error = _authenticate(request)
    if error:
        return error

    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'error': 'invalid json'}, status=400)

    events = body.get('events') or []
    if not isinstance(events, list):
        return JsonResponse({'status': 'error', 'error': 'events must be a list'}, status=400)
    if len(events) > MAX_PUSH_EVENTS:
        return JsonResponse({'status': 'error', 'error': 'too many events'}, status=413)

    accepted, duplicates, failed = [], [], []
    for item in events:
        event_uuid = str(item.get('uuid') or '').strip()
        entity = str(item.get('entity') or '').strip()
        op = str(item.get('op') or '').strip()

        if not event_uuid or entity not in SUPPORTED_ENTITIES:
            failed.append({'uuid': event_uuid, 'error': 'unsupported entity'})
            continue

        if PosEvent.objects.filter(uuid=event_uuid).exists():
            duplicates.append(event_uuid)
            continue

        payload = item.get('payload')
        if not isinstance(payload, dict):
            failed.append({'uuid': event_uuid, 'error': 'payload must be an object'})
            continue

        try:
            with transaction.atomic():
                event = PosEvent.objects.create(
                    uuid=event_uuid,
                    entity=entity,
                    entity_uuid=str(item.get('entity_uuid') or '')[:64],
                    op=op,
                    payload=payload,
                    device_id=device.device_id,
                    user_name=str(item.get('user_name') or '')[:100],
                    created_at=_parse_ts(item.get('created_at')),
                )
                _materialize(event)
            accepted.append(event_uuid)
        except Exception as exc:
            logger.exception('pos_push failed for event %s', event_uuid)
            failed.append({'uuid': event_uuid, 'error': str(exc)[:200]})

    _touch(device)
    return JsonResponse({
        'status': 'ok',
        'accepted': accepted,
        'duplicates': duplicates,
        'failed': failed,
        'server_seq': PosEvent.objects.order_by('-seq').values_list('seq', flat=True).first() or 0,
    })


@require_GET
def pos_pull(request):
    """تسحب الحاسبة ما رفعته الحاسبة الأخرى (وأحداث الموقع) بعد مؤشرها."""
    device, error = _authenticate(request)
    if error:
        return error

    try:
        since = max(0, int(request.GET.get('since', 0)))
    except (TypeError, ValueError):
        since = 0
    try:
        limit = min(MAX_PULL_LIMIT, max(1, int(request.GET.get('limit', MAX_PULL_LIMIT))))
    except (TypeError, ValueError):
        limit = MAX_PULL_LIMIT

    # نتجاوز أحداث الجهاز نفسه — عنده أصلها. لكن المؤشر يتقدّم فوقها
    # وإلا بقيت الحاسبة تطلب نفس المدى إلى الأبد.
    window = list(PosEvent.objects.filter(seq__gt=since).order_by('seq')[:limit])
    outgoing = [event for event in window if event.device_id != device.device_id]
    next_since = window[-1].seq if window else since
    has_more = PosEvent.objects.filter(seq__gt=next_since).exists()

    _touch(device)
    return JsonResponse({
        'status': 'ok',
        'events': [
            {
                'seq': event.seq,
                'uuid': event.uuid,
                'entity': event.entity,
                'entity_uuid': event.entity_uuid,
                'op': event.op,
                'payload': event.payload,
                'device_id': event.device_id,
                'user_name': event.user_name,
                'created_at': event.created_at,
            }
            for event in outgoing
        ],
        'next_since': next_since,
        'has_more': has_more,
    })


@require_GET
def pos_version(request):
    """أحدث إصدار منشور من البرنامج. تسأل عنه كل حاسبة عند التشغيل."""
    device, error = _authenticate(request)
    if error:
        return error

    releases = [r for r in AppRelease.objects.filter(is_active=True).exclude(installer='')]
    if not releases:
        return JsonResponse({'status': 'ok', 'latest': None})

    latest = max(releases, key=lambda release: release.version_tuple)
    return JsonResponse({
        'status': 'ok',
        'latest': {
            'version': latest.version,
            'url': request.build_absolute_uri(latest.installer.url),
            'sha256': latest.sha256,
            'size_bytes': latest.size_bytes,
            'notes': latest.notes,
            'mandatory': latest.is_mandatory,
        },
    })


@require_GET
def pos_ping(request):
    """فحص سريع للاتصال وصلاحية الرمز — يستعمله مؤشر الحالة في البرنامج."""
    device, error = _authenticate(request)
    if error:
        return error
    _touch(device)
    return JsonResponse({
        'status': 'ok',
        'device': device.name,
        'server_time': timezone.now().isoformat(),
        'server_seq': PosEvent.objects.order_by('-seq').values_list('seq', flat=True).first() or 0,
    })


# ---------------------------------------------------------------- طلبات الموقع

def record_online_order_moves(order):
    """كل طلب من الموقع يصبح حركة مخزون تصل للحاسبتين عند أول مزامنة.
    هذا ما يمنع بيع قطعة في المحل بعد أن اشتراها زبون من الموقع.
    آمن: لا يُفشل إنشاء الطلب مهما حدث."""
    import uuid as uuid_module

    created = []
    try:
        for item in order.items.select_related('product'):
            product = item.product
            if not product:
                continue
            move_uuid = str(uuid_module.uuid4())
            now = timezone.now().isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            StockMove.objects.create(
                uuid=move_uuid,
                product=product,
                product_uuid=str(product.uuid),
                delta=-int(item.quantity or 0),
                reason='online_order',
                ref_type='order',
                ref_uuid=str(order.uuid),
                note=f'طلب الموقع رقم {order.id}',
                device_id='website',
                created_at=now,
            )
            recompute_product_quantity(str(product.uuid))
            PosEvent.objects.create(
                uuid=str(uuid_module.uuid4()),
                entity='stock_move',
                entity_uuid=move_uuid,
                op='insert',
                payload={
                    'uuid': move_uuid,
                    'product_uuid': str(product.uuid),
                    'delta': -int(item.quantity or 0),
                    'reason': 'online_order',
                    'ref_type': 'order',
                    'ref_uuid': str(order.uuid),
                    'note': f'طلب الموقع رقم {order.id}',
                    'device_id': 'website',
                    'created_at': now,
                },
                device_id='website',
                created_at=now,
            )
            created.append(move_uuid)
    except Exception:
        logger.exception('failed to record stock moves for order %s', getattr(order, 'id', '?'))
    return created
