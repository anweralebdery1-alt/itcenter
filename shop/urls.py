from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from store import views
from store.sitemaps import SITEMAPS


urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('manifest.webmanifest', views.manifest, name='manifest'),
    path('sw.js', views.service_worker, name='service_worker'),
    path('app/', views.install_app, name='install_app'),
    path('', views.home, name='home'),
    path('courses/', views.courses, name='courses'),
    path('videos/', views.videos, name='videos'),
    path('videos/<int:pk>/', views.video_detail, name='video_detail'),
    path('about/', views.about, name='about'),
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
    path('api/', include('store.api_urls')),
]

if settings.SERVE_MEDIA_WITH_DJANGO:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
