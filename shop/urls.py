from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from store import chat, mobile_pos, views
from store.sitemaps import SITEMAPS


urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('manifest.webmanifest', views.manifest, name='manifest'),
    path('sw.js', views.service_worker, name='service_worker'),
    path('push-sw.js', views.push_sw, name='push_sw'),
    path('push/', views.push_page, name='push_page'),
    path('push/subscribe/', views.push_subscribe, name='push_subscribe'),
    path('app/', views.install_app, name='install_app'),
    path('', views.home, name='home'),
    path('courses/', views.courses, name='courses'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/<int:pk>/register/', views.register_course, name='register_course'),
    path('courses/<int:pk>/review/', views.submit_course_review, name='submit_course_review'),
    path('videos/', views.videos, name='videos'),
    path('videos/<int:pk>/', views.video_detail, name='video_detail'),
    path('about/', views.about, name='about'),
    path('graduation-projects/', views.graduation_projects, name='graduation_projects'),
    path('account/', views.account, name='account'),
    path('account/details/', views.account_details, name='account_details'),
    path('account/logout/', views.account_logout, name='account_logout'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/<int:pk>/review/', views.submit_review, name='submit_review'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:pk>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:pk>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout_phone, name='checkout_phone'),
    path('checkout/otp/', views.checkout_otp, name='checkout_otp'),
    path('checkout/otp/resend/', views.resend_otp, name='resend_otp'),
    path('checkout/details/', views.checkout_details, name='checkout_details'),
    path('order/<int:order_id>/success/', views.order_success, name='order_success'),
    path('order/<int:order_id>/payment/', views.payment_redirect, name='payment_redirect'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/cancel/', views.order_cancel, name='order_cancel'),
    path('order/<int:order_id>/reorder/', views.order_reorder, name='order_reorder'),
    path('chat/state/', chat.chat_state, name='chat_state'),
    path('chat/send/', chat.chat_send, name='chat_send'),
    # البيع من الهاتف (أنور ومهند) — يكتب أحداث البرنامج نفسها
    path('pos/', mobile_pos.pos_home, name='mobile_pos'),
    path('pos/manifest.webmanifest', mobile_pos.pos_manifest, name='mobile_pos_manifest'),
    path('pos/receipt/<uuid:sale_uuid>/', mobile_pos.pos_receipt, name='mobile_pos_receipt'),
    path('pos/api/products/', mobile_pos.api_products, name='mobile_pos_products'),
    path('pos/api/sale/', mobile_pos.api_sale, name='mobile_pos_sale'),
    path('pos/api/sales/', mobile_pos.api_sales, name='mobile_pos_sales'),
    path('pos/api/projects/', mobile_pos.api_projects, name='mobile_pos_projects'),
    path('pos/api/projects/save/', mobile_pos.api_project_save, name='mobile_pos_project_save'),
    path('pos/api/projects/payment/', mobile_pos.api_project_payment, name='mobile_pos_project_payment'),
    path('api/', include('store.api_urls')),
]

if settings.SERVE_MEDIA_WITH_DJANGO:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
