from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Product


class ProductSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8
    protocol = 'https'

    def items(self):
        return Product.objects.filter(quantity__gt=0).order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class StaticViewSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        return ['home', 'courses', 'videos', 'about']

    def location(self, item):
        return reverse(item)


SITEMAPS = {
    'products': ProductSitemap,
    'pages': StaticViewSitemap,
}
