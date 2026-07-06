from django.core.management.base import BaseCommand
from django.db.models import Q

from store.models import Product


class Command(BaseCommand):
    help = 'يولّد الصور المصغّرة الخفيفة للمنتجات التي لا تملك مصغّرة بعد.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true',
                            help='إعادة توليد المصغّرة لكل المنتجات حتى الموجودة.')

    def handle(self, *args, **options):
        qs = Product.objects.exclude(image='').exclude(image__isnull=True)
        if not options['all']:
            qs = qs.filter(Q(thumbnail='') | Q(thumbnail__isnull=True))
        total = qs.count()
        done = 0
        for product in qs.iterator():
            if options['all']:
                product.thumbnail = None
            product._ensure_thumbnail()
            done += 1
            if done % 20 == 0:
                self.stdout.write(f'{done}/{total} ...')
        self.stdout.write(self.style.SUCCESS(f'تم توليد {done} صورة مصغّرة من أصل {total}.'))
