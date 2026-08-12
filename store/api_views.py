"""واجهة المتجر العامة — قراءة فقط.

المسارات القديمة التي كانت تُعدّل المخزون بالرمز المشترك حُذفت؛ مزامنة نقاط
البيع كلها في pos_sync.py برمز خاص لكل حاسبة. لا تُضف هنا أي مسار يكتب.
"""

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .models import Product
from .serializers import ProductSerializer


@require_GET
def products_list(request):
    query = request.GET.get('search', '').strip()
    products = Product.objects.visible().order_by('-created_at')
    if query:
        products = products.filter(name__icontains=query)
    if request.GET.get('tab', 'all') == 'offers':
        products = products.filter(is_offer=True)

    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per = int(request.GET.get('per', 20))
    except (TypeError, ValueError):
        per = 20
    per = min(max(per, 1), 100)

    paginator = Paginator(products, per)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'count': paginator.count,
        'results': ProductSerializer(page_obj.object_list, many=True).data,
    })


@require_GET
def product_detail_api(request, pk):
    product = get_object_or_404(Product.objects.visible(), pk=pk)
    return JsonResponse(ProductSerializer(product).data, safe=False)
