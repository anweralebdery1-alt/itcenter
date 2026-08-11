from django.urls import path
from . import api_views, pos_sync
urlpatterns = [
    # مزامنة نقاط البيع (الحاسبتان) — السجل الكامل للنظام
    path('pos/push/', pos_sync.pos_push, name='api_pos_push'),
    path('pos/pull/', pos_sync.pos_pull, name='api_pos_pull'),
    path('pos/ping/', pos_sync.pos_ping, name='api_pos_ping'),
    path('products/', api_views.products_list, name='api_products'),
    path('products/<int:pk>/', api_views.product_detail_api, name='api_product_detail'),
    path('reserve/', api_views.reserve, name='api_reserve'),
    path('sync/push/', api_views.sync_push, name='api_sync_push'),
    path('sync/pull/', api_views.sync_pull, name='api_sync_pull'),
    path('stock_snapshot/', api_views.stock_snapshot, name='api_stock_snapshot'),
    path('orders/pending_count/', api_views.pending_orders_count, name='api_pending_orders_count'),
    path('stock_update/', api_views.stock_update, name='api_stock_update'),
]
