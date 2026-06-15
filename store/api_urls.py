from django.urls import path
from . import api_views
urlpatterns = [
    path('products/', api_views.products_list, name='api_products'),
    path('products/<int:pk>/', api_views.product_detail_api, name='api_product_detail'),
    path('reserve/', api_views.reserve, name='api_reserve'),
    path('sync/push/', api_views.sync_push, name='api_sync_push'),
    path('sync/pull/', api_views.sync_pull, name='api_sync_pull'),
    path('stock_snapshot/', api_views.stock_snapshot, name='api_stock_snapshot'),
    path('stock_update/', api_views.stock_update, name='api_stock_update'),
]
