from django.urls import path
from . import api_views, pos_sync
urlpatterns = [
    # مزامنة نقاط البيع (الحاسبتان) — السجل الكامل للنظام
    path('pos/push/', pos_sync.pos_push, name='api_pos_push'),
    path('pos/pull/', pos_sync.pos_pull, name='api_pos_pull'),
    path('pos/ping/', pos_sync.pos_ping, name='api_pos_ping'),
    path('pos/version/', pos_sync.pos_version, name='api_pos_version'),
    path('pos/orders_count/', pos_sync.pos_orders_count, name='api_pos_orders_count'),

    # واجهة المتجر للقراءة فقط — لا تكشف سعر الشراء
    path('products/', api_views.products_list, name='api_products'),
    path('products/<int:pk>/', api_views.product_detail_api, name='api_product_detail'),

    # عدّاد الطلبات: يبقى بمساره القديم لتوافق النسخ القديمة من البرنامج،
    # لكن بمصادقة رمز الجهاز لا الرمز المشترك.
    path('orders/pending_count/', pos_sync.pos_orders_count,
         name='api_pending_orders_count'),

    # المسارات القديمة (stock_update · stock_snapshot · sync/push · sync/pull ·
    # reserve) حُذفت. كانت محميّة برمز مشترك واحد وُزّع داخل المُثبِّتات، وكان
    # يسمح بقراءة أسعار الشراء وتعديل المخزون. بديلها /api/pos/* برمز لكل جهاز.
]
