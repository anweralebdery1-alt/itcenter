import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Product, SaleReservation
from .serializers import ProductSerializer
from django.core.paginator import Paginator

PRODUCT_TABLE_NAMES = ('products', 'product', 'store_product')


def _auth_token(request):
    header = request.headers.get('Authorization', '')
    if not header:
        return ''
    return header.split()[-1]


def _require_sync_token(request):
    return _auth_token(request) == settings.SYNC_API_TOKEN


def _as_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _product_payload(data):
    raw_local = data.get('local_id') or data.get('id') or data.get('pk')
    try:
        local_id = int(str(raw_local).strip()) if str(raw_local).strip() != '' and raw_local is not None else None
    except (TypeError, ValueError):
        local_id = None
    raw_sku = str(data.get('sku') or data.get('SKU') or '').strip()
    # نخزّن SKU الحقيقي كما هو؛ المطابقة تتم عبر local_id لذا يُسمح بتكرار الـSKU
    sku = raw_sku or (str(local_id) if local_id is not None else '')
    if local_id is None and not sku:
        return None, 'missing sku/local_id'

    return {
        'local_id': local_id,
        'sku': sku,
        'name': str(data.get('name') or data.get('title') or 'Unnamed').strip() or 'Unnamed',
        'description': str(data.get('description') or ''),
        'buy_price': _as_float(data.get('buy_price'), 0),
        'sell_price': _as_float(data.get('sell_price', data.get('price')), 0),
        'quantity': _as_int(data.get('quantity', data.get('qty')), 0),
    }, None


def _upsert_product(data):
    payload, error = _product_payload(data)
    if error:
        return None, error
    defaults = {
        'sku': payload['sku'],
        'name': payload['name'],
        'description': payload['description'],
        'buy_price': payload['buy_price'],
        'sell_price': payload['sell_price'],
        'quantity': payload['quantity'],
    }
    if payload['local_id'] is not None:
        # المطابقة عبر المعرف المحلي → منتجان بنفس الـSKU يبقيان منفصلين
        prod, created = Product.objects.update_or_create(
            local_id=payload['local_id'], defaults=defaults,
        )
    else:
        # لا يوجد معرف محلي (مثلاً منتج أُضيف من لوحة الإدارة) → المطابقة عبر SKU
        defaults.pop('sku')
        prod, created = Product.objects.update_or_create(
            sku=payload['sku'], defaults=defaults,
        )
    return {'action': 'insert' if created else 'update', 'sku': prod.sku, 'local_id': prod.local_id, 'quantity': prod.quantity}, None

def products_list(request):
    q = request.GET.get('search','').strip()
    qs = Product.objects.all().order_by('-created_at')
    if q:
        qs = qs.filter(name__icontains=q)[:50]
    tab = request.GET.get('tab','all')
    if tab == 'offers':
        qs = qs.filter(is_offer=True)
    page = int(request.GET.get('page',1))
    per = int(request.GET.get('per',20))
    paginator = Paginator(qs, per)
    page_obj = paginator.get_page(page)
    data = ProductSerializer(page_obj.object_list, many=True).data
    return JsonResponse({'count': paginator.count, 'results': data})

def product_detail_api(request, pk):
    p = get_object_or_404(Product, pk=pk)
    return JsonResponse(ProductSerializer(p).data, safe=False)

@csrf_exempt
def reserve(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        full_name = payload.get('full_name') or payload.get('name')
        phone = payload.get('phone')
        items = payload.get('items', [])
        total = float(payload.get('total',0))
        user_id = payload.get('user_id')
        res = SaleReservation.objects.create(full_name=full_name, phone=phone, items=items, total=total)
        return JsonResponse({'status':'ok','id': str(res.uuid)})
    except Exception as e:
        return JsonResponse({'status':'error','error': str(e)})

@csrf_exempt
def sync_push(request):
    if not _require_sync_token(request):
        return JsonResponse({'status':'error','error':'invalid token'}, status=401)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        device_id = payload.get('device_id','unknown')
        changes = payload.get('changes', [])
        applied = []
        errors = []
        for ch in changes:
            table = ch.get('table')
            op = ch.get('operation')
            data = ch.get('data', {})
            if table in PRODUCT_TABLE_NAMES and op in ('update','insert','upsert'):
                result, err = _upsert_product(data)
                if err:
                    errors.append({'change': ch, 'error': err})
                else:
                    applied.append(result)
            elif table in PRODUCT_TABLE_NAMES and op == 'delete':
                sku = str(data.get('sku') or data.get('local_id') or data.get('id') or data.get('pk') or '').strip()
                if not sku:
                    errors.append({'change': ch, 'error':'missing sku/local_id'})
                    continue
                deleted, _ = Product.objects.filter(sku=sku).delete()
                applied.append({'action':'delete','sku':sku,'deleted':deleted})
            elif table == 'sales' and op=='insert':
                try:
                    items = data.get('items', [])
                    total = float(data.get('total') or 0)
                    buyer = data.get('buyer') or data.get('full_name') or 'POS'
                    phone = data.get('phone','')
                    SaleReservation.objects.create(full_name=buyer, phone=phone, items=items, total=total, status='processed')
                    applied.append({'action':'sale_insert','buyer':buyer})
                except Exception as e:
                    errors.append({'change': ch, 'error': str(e)})
            else:
                errors.append({'change': ch, 'error':'unsupported table/op'})
        return JsonResponse({'status':'ok','applied':applied,'errors':errors})
    except Exception as e:
        return JsonResponse({'status':'error','error': str(e)})

def sync_pull(request):
    since = request.GET.get('since')
    try:
        qs = Product.objects.all().order_by('-updated_at')[:100]
        data = ProductSerializer(qs, many=True).data
        return JsonResponse({'status':'ok','changes': data})
    except Exception as e:
        return JsonResponse({'status':'error','error': str(e)})


def stock_snapshot(request):
    data = [
        {
            'local_id': p.local_id,
            'sku': p.sku,
            'name': p.name,
            'buy_price': p.buy_price,
            'sell_price': p.sell_price,
            'price': p.sell_price,
            'quantity': p.quantity,
            'qty': p.quantity,
            'updated_at': p.updated_at.isoformat(),
        }
        for p in Product.objects.all().order_by('local_id', 'sku')
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def stock_update(request):
    if not _require_sync_token(request):
        return JsonResponse({'status':'error','error':'invalid token'}, status=401)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        if isinstance(payload, dict):
            items = payload.get('products') or payload.get('changes') or []
        else:
            items = payload
        applied, errors = [], []
        for item in items:
            # حذف فعلي من الموقع عند وصول علامة الحذف (المطابقة عبر local_id أولاً)
            if isinstance(item, dict) and (item.get('_delete') or item.get('deleted')):
                raw_local = item.get('local_id') or item.get('id') or item.get('pk')
                try:
                    lid = int(str(raw_local).strip()) if str(raw_local).strip() != '' and raw_local is not None else None
                except (TypeError, ValueError):
                    lid = None
                if lid is not None:
                    deleted, _ = Product.objects.filter(local_id=lid).delete()
                    applied.append({'action': 'delete', 'local_id': lid, 'deleted': deleted})
                    continue
                sku = str(item.get('sku') or '').strip()
                if not sku:
                    errors.append({'item': item, 'error': 'missing local_id/sku for delete'})
                    continue
                deleted, _ = Product.objects.filter(sku=sku).delete()
                applied.append({'action': 'delete', 'sku': sku, 'deleted': deleted})
                continue
            result, err = _upsert_product(item)
            if err:
                errors.append({'item': item, 'error': err})
            else:
                applied.append(result)
        return JsonResponse({'status':'ok','applied':applied,'errors':errors})
    except Exception as e:
        return JsonResponse({'status':'error','error': str(e)})
