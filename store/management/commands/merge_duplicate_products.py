import sys

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from store.models import Product, StockMove
from store.pos_sync import recompute_product_quantity

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


class Command(BaseCommand):
    help = (
        'يدمج المنتجات المكرّرة الناتجة عن انتقال المزامنة من المطابقة بـlocal_id '
        'إلى المطابقة بـuuid. يُبقي الصف القديم (بصوره ووصفه وتصنيفه) ويمنحه '
        'المعرّف الجديد، ثم يحذف الصف الفارغ.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='نفّذ الدمج فعلياً (بدونه عرض فقط).')

    def handle(self, *args, **options):
        apply_changes = options['apply']

        # الأزواج: صف قديم (له local_id) وصف جديد (بلا local_id) بنفس الاسم والـSKU
        legacy = Product.objects.filter(local_id__isnull=False, deleted_at__isnull=True)
        pairs, ambiguous = [], []

        for old in legacy:
            candidates = list(Product.objects.filter(
                local_id__isnull=True, deleted_at__isnull=True,
                name=old.name, sku=old.sku,
            ))
            if len(candidates) == 1:
                pairs.append((old, candidates[0]))
            elif len(candidates) > 1:
                ambiguous.append((old, candidates))

        if not pairs and not ambiguous:
            self.stdout.write('✅ لا توجد منتجات مكرّرة.')
            return

        self.stdout.write(f'المنتجات المكرّرة: {len(pairs)}\n')
        for old, new in pairs:
            has_image = 'صورة ✅' if old.image else 'بلا صورة'
            self.stdout.write(
                f'  {old.name[:36]:<36} [SKU {old.sku}]  '
                f'يبقى local_id={old.local_id} ({has_image}) '
                f'ويأخذ المعرّف {str(new.uuid)[:8]}…'
            )

        if ambiguous:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️ {len(ambiguous)} حالة ملتبسة (أكثر من مطابق) — تُركت بلا تغيير:'))
            for old, candidates in ambiguous:
                self.stdout.write(f'   {old.name} — {len(candidates)} مطابقين')

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                '\n(عرض فقط — لم يتغيّر شيء. أضف --apply للتنفيذ.)'))
            return

        merged = 0
        for old, new in pairs:
            with transaction.atomic():
                new_uuid = new.uuid
                # حركات المخزون تشير للصف الجديد → نعيد ربطها بالصف الباقي
                StockMove.objects.filter(product=new).update(product=old)
                stamp = new.pos_updated_at
                sell, buy = new.sell_price, new.buy_price
                new.delete()                       # يحرّر المعرّف الفريد
                old.uuid = new_uuid
                old.pos_updated_at = stamp
                old.sell_price = sell
                old.buy_price = buy
                old.save(update_fields=['uuid', 'pos_updated_at', 'sell_price', 'buy_price'])
                recompute_product_quantity(str(new_uuid))
            merged += 1

        self.stdout.write(self.style.SUCCESS(f'\n✅ دُمج {merged} منتجاً.'))

        remaining = Product.objects.visible().count()
        duplicates = (Product.objects.visible()
                      .values('name', 'sku')
                      .annotate(total=Count('id')).filter(total__gt=1).count())
        self.stdout.write(f'   المنتجات الظاهرة الآن: {remaining}')
        self.stdout.write(f'   ما زال مكرّراً: {duplicates}')
