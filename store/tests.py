import io
import json
import tempfile
from html import unescape

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .image_processing import (
    CANVAS_SIZE,
    FOOTER_TEXT,
    MAX_OUTPUT_BYTES,
    prepare_product_image,
)
from .admin import ProductAdminForm
from .models import Product, ProductImage


def _uploaded_test_image(width=1800, height=1200):
    image = Image.new("RGB", (width, height), (235, 240, 245))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return SimpleUploadedFile(
        "sample-product.png",
        buffer.getvalue(),
        content_type="image/png",
    )


class ProductImageProcessingTests(TestCase):
    def test_processor_creates_small_square_branded_image(self):
        uploaded = _uploaded_test_image()
        output, extension = prepare_product_image(uploaded)

        self.assertEqual(extension, "jpg")
        self.assertLessEqual(output.getbuffer().nbytes, MAX_OUTPUT_BYTES)
        self.assertEqual(
            FOOTER_TEXT,
            "مركز آي تي للتطوير والتدريب - النجف الاشرف -",
        )
        with Image.open(output) as image:
            self.assertEqual(image.size, (CANVAS_SIZE, CANVAS_SIZE))
            self.assertEqual(image.format, "JPEG")

    def test_product_save_processes_new_upload_only(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                product = Product.objects.create(
                    name="Test product",
                    sku="TEST-IMAGE",
                    sell_price=1000,
                    quantity=3,
                    image=_uploaded_test_image(),
                )
                original_name = product.image.name

                self.assertTrue(original_name.endswith(".jpg"))
                with Image.open(product.image.path) as image:
                    self.assertEqual(image.size, (CANVAS_SIZE, CANVAS_SIZE))

                product.sell_price = 1500
                product.save()
                product.refresh_from_db()
                self.assertEqual(product.image.name, original_name)


class ProductAvailabilityDisplayTests(TestCase):
    def test_storefront_hides_exact_stock_quantity(self):
        available = Product.objects.create(
            name="Available product",
            sku="AVAILABLE",
            sell_price=1000,
            quantity=37,
            reviewed=True,
        )
        Product.objects.create(
            name="Unavailable product",
            sku="UNAVAILABLE",
            sell_price=1000,
            quantity=0,
            reviewed=True,
        )

        home_response = self.client.get("/")
        self.assertContains(home_response, "● متوفر")
        self.assertContains(home_response, "● غير متوفر")
        self.assertNotContains(home_response, "متوفر 37")

        detail_response = self.client.get(f"/product/{available.pk}/")
        self.assertContains(detail_response, ">متوفر</span>", html=False)
        self.assertNotContains(detail_response, "متوفر في المخزن")


class ProductGalleryTests(TestCase):
    def test_gallery_accepts_nine_extra_images_and_rejects_the_tenth(self):
        """الحد الأقصى عشر صور: الرئيسية + تسع في المعرض."""
        from .models import MAX_GALLERY_IMAGES, MAX_PRODUCT_IMAGES

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                product = Product.objects.create(
                    name="Gallery product",
                    sku="GALLERY",
                    sell_price=1000,
                    quantity=5,
                    image=_uploaded_test_image(800, 800),
                    reviewed=True,
                )
                for position in range(1, MAX_GALLERY_IMAGES + 1):
                    ProductImage.objects.create(
                        product=product,
                        image=_uploaded_test_image(800, 800),
                        position=position,
                    )

                self.assertEqual(product.gallery_images.count(), MAX_GALLERY_IMAGES)
                first_gallery_image = product.gallery_images.first()
                with Image.open(first_gallery_image.image.path) as image:
                    self.assertEqual(image.size, (CANVAS_SIZE, CANVAS_SIZE))

                response = self.client.get(f"/product/{product.pk}/")
                self.assertEqual(response.content.count(b'data-image='),
                                 MAX_PRODUCT_IMAGES)

                with self.assertRaises(ValidationError):
                    ProductImage.objects.create(
                        product=product,
                        image=_uploaded_test_image(800, 800),
                        position=1,
                    )


class ProductAdminSpecificationsTests(TestCase):
    def test_plain_lines_are_saved_as_structured_specifications(self):
        form = ProductAdminForm(
            data={
                'name': 'Arduino board',
                'sku': 'ARD-1',
                'description': 'Test',
                'specifications_text': (
                    'نوع المتحكم: Arduino Uno\n'
                    'جهد التشغيل = 5V\n'
                    'اللون： أزرق'
                ),
                'buy_price': 1000,
                'sell_price': 1500,
                'quantity': 4,
                'is_offer': False,
                'category': '',
                            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertEqual(
            product.specifications,
            {
                'نوع المتحكم': 'Arduino Uno',
                'جهد التشغيل': '5V',
                'اللون': 'أزرق',
            },
        )

    def test_invalid_line_has_clear_validation_error(self):
        form = ProductAdminForm(
            data={
                'name': 'Arduino board',
                'sku': 'ARD-2',
                'description': '',
                'specifications_text': 'سطر بلا فاصل',
                'buy_price': 1000,
                'sell_price': 1500,
                'quantity': 4,
                'is_offer': False,
                'category': '',
                            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('السطر 1 غير صحيح', form.errors['specifications_text'][0])


class PosSyncTests(TestCase):
    """اختبارات مزامنة نقاط البيع — العقد الذي تعتمد عليه الحاسبتان."""

    def setUp(self):
        import secrets

        from .models import PosDevice
        self.device_a = PosDevice.objects.create(
            device_id='device-a', name='حاسبة أنور', token=secrets.token_hex(16))
        self.device_b = PosDevice.objects.create(
            device_id='device-b', name='حاسبة مهند', token=secrets.token_hex(16))

    def _auth(self, device):
        return {'HTTP_AUTHORIZATION': f'Token {device.token}'}

    def _event(self, entity, op, entity_uuid, payload, event_uuid=None):
        import uuid as uuid_module
        return {
            'uuid': event_uuid or str(uuid_module.uuid4()),
            'entity': entity, 'op': op, 'entity_uuid': entity_uuid,
            'payload': payload, 'created_at': '2026-08-10T10:00:00.000Z',
        }

    def _push(self, device, events):
        import json
        return self.client.post(
            '/api/pos/push/', data=json.dumps({'events': events}),
            content_type='application/json', **self._auth(device))

    def test_product_sku_event_changes_only_the_sku(self):
        """إعادة ترتيب الحافظات: يتغيّر SKU وحده، ويبقى اسم الموقع وأسعاره كما هي،
        ويصل الحدث للحاسبة الأخرى."""
        from .models import Product
        product = Product.objects.create(name='اسم الموقع المنقّح', sku='137',
                                         buy_price=5000, sell_price=8000, quantity=3)
        uid = str(product.uuid)
        response = self._push(self.device_a, [self._event('product_sku', 'update', uid, {
            'uuid': uid, 'sku': '324', 'old_sku': '137', 'updated_at': '2026-10-31T10:00:00.000Z'})])
        self.assertEqual(response.json()['accepted'].__len__(), 1)
        product.refresh_from_db()
        self.assertEqual(product.sku, '324')
        self.assertEqual(product.name, 'اسم الموقع المنقّح')
        self.assertEqual((product.buy_price, product.sell_price), (5000, 8000))

        pulled = self.client.get('/api/pos/pull/', {'since': 0}, **self._auth(self.device_b)).json()
        self.assertIn('product_sku', [e['entity'] for e in pulled['events']])

    def test_push_requires_a_valid_device_token(self):
        response = self.client.post('/api/pos/push/', data='{"events": []}',
                                    content_type='application/json',
                                    HTTP_AUTHORIZATION='Token wrong-token')
        self.assertEqual(response.status_code, 401)

    def test_disabled_device_cannot_sync(self):
        self.device_a.is_active = False
        self.device_a.save(update_fields=['is_active'])
        self.assertEqual(self._push(self.device_a, []).status_code, 401)

    def test_quantity_is_built_from_the_movement_ledger(self):
        import uuid as uuid_module

        from .models import Product
        product_uuid = str(uuid_module.uuid4())
        self._push(self.device_a, [
            self._event('product', 'insert', product_uuid, {
                'uuid': product_uuid, 'name': 'أردوينو UNO', 'sku': '8',
                'buy_price': 10000, 'sell_price': 15000,
                'updated_at': '2026-08-10T10:00:00.000Z'}),
            self._event('stock_move', 'insert', 'm1', {
                'uuid': 'm1', 'product_uuid': product_uuid, 'delta': 5,
                'reason': 'opening', 'created_at': '2026-08-10T10:00:00.000Z'}),
        ])
        self.assertEqual(Product.objects.get(uuid=product_uuid).quantity, 5)

        # بيعتان من حاسبتين مختلفتين بلا إنترنت → تُجمعان ولا تضيع واحدة
        self._push(self.device_a, [self._event('stock_move', 'insert', 'm2', {
            'uuid': 'm2', 'product_uuid': product_uuid, 'delta': -2, 'reason': 'sale',
            'created_at': '2026-08-10T11:00:00.000Z'})])
        self._push(self.device_b, [self._event('stock_move', 'insert', 'm3', {
            'uuid': 'm3', 'product_uuid': product_uuid, 'delta': -1, 'reason': 'sale',
            'created_at': '2026-08-10T11:00:00.000Z'})])
        self.assertEqual(Product.objects.get(uuid=product_uuid).quantity, 2)

    def test_resending_the_same_event_changes_nothing(self):
        import uuid as uuid_module

        from .models import Product, StockMove
        product_uuid = str(uuid_module.uuid4())
        move = self._event('stock_move', 'insert', 'm1', {
            'uuid': 'm1', 'product_uuid': product_uuid, 'delta': 5,
            'reason': 'opening', 'created_at': '2026-08-10T10:00:00.000Z'})
        self._push(self.device_a, [
            self._event('product', 'insert', product_uuid, {
                'uuid': product_uuid, 'name': 'منتج', 'sku': '1',
                'updated_at': '2026-08-10T10:00:00.000Z'}),
            move,
        ])
        # الإنترنت المتقطّع يُعيد إرسال نفس الحدث — يجب ألا يتضاعف المخزون
        response = self._push(self.device_a, [move])
        self.assertEqual(response.json()['duplicates'], [move['uuid']])
        self.assertEqual(response.json()['accepted'], [])
        self.assertEqual(StockMove.objects.filter(product_uuid=product_uuid).count(), 1)
        self.assertEqual(Product.objects.get(uuid=product_uuid).quantity, 5)

    def test_deleting_one_product_keeps_others_with_the_same_sku(self):
        import uuid as uuid_module

        from .models import Product
        first, second = str(uuid_module.uuid4()), str(uuid_module.uuid4())
        for product_uuid, name in ((first, 'أردوينو'), (second, 'حسّاس')):
            self._push(self.device_a, [self._event('product', 'insert', product_uuid, {
                'uuid': product_uuid, 'name': name, 'sku': '8',
                'updated_at': '2026-08-10T10:00:00.000Z'})])

        self._push(self.device_a, [self._event('product', 'delete', first, {'uuid': first})])

        self.assertIsNotNone(Product.objects.get(uuid=first).deleted_at)
        self.assertIsNone(Product.objects.get(uuid=second).deleted_at)
        self.assertEqual([p.name for p in Product.objects.visible()], ['حسّاس'])

    def test_pull_delivers_the_other_device_changes_only(self):
        import uuid as uuid_module

        product_uuid = str(uuid_module.uuid4())
        self._push(self.device_a, [self._event('product', 'insert', product_uuid, {
            'uuid': product_uuid, 'name': 'منتج أنور', 'sku': '1',
            'updated_at': '2026-08-10T10:00:00.000Z'})])

        own = self.client.get('/api/pos/pull/?since=0', **self._auth(self.device_a)).json()
        self.assertEqual(own['events'], [])
        self.assertGreater(own['next_since'], 0)   # المؤشر يتقدّم فلا تتكرر الطلبات

        other = self.client.get('/api/pos/pull/?since=0', **self._auth(self.device_b)).json()
        self.assertEqual(len(other['events']), 1)
        self.assertEqual(other['events'][0]['payload']['name'], 'منتج أنور')

    def test_older_edit_never_overwrites_a_newer_one(self):
        import uuid as uuid_module

        from .models import Product
        product_uuid = str(uuid_module.uuid4())
        self._push(self.device_a, [self._event('product', 'insert', product_uuid, {
            'uuid': product_uuid, 'name': 'الاسم الأحدث', 'sku': '1',
            'sell_price': 20000, 'updated_at': '2026-08-10T12:00:00.000Z'})])
        # تعديل أقدم يصل متأخراً من الحاسبة الأخرى
        self._push(self.device_b, [self._event('product', 'update', product_uuid, {
            'uuid': product_uuid, 'name': 'الاسم الأقدم', 'sku': '1',
            'sell_price': 5000, 'updated_at': '2026-08-10T09:00:00.000Z'})])

        product = Product.objects.get(uuid=product_uuid)
        self.assertEqual(product.name, 'الاسم الأحدث')
        self.assertEqual(product.sell_price, 20000)

    def test_online_order_reduces_stock_and_reaches_the_devices(self):
        import uuid as uuid_module

        from .models import Order, OrderItem, PosEvent, Product
        from .pos_sync import record_online_order_moves
        product_uuid = str(uuid_module.uuid4())
        self._push(self.device_a, [
            self._event('product', 'insert', product_uuid, {
                'uuid': product_uuid, 'name': 'منتج', 'sku': '1', 'sell_price': 1000,
                'updated_at': '2026-08-10T10:00:00.000Z'}),
            self._event('stock_move', 'insert', 'm1', {
                'uuid': 'm1', 'product_uuid': product_uuid, 'delta': 4,
                'reason': 'opening', 'created_at': '2026-08-10T10:00:00.000Z'}),
        ])
        product = Product.objects.get(uuid=product_uuid)

        order = Order.objects.create(full_name='زبون', phone='9647800000000',
                                     province='النجف', address='عنوان', total=1000)
        OrderItem.objects.create(order=order, product=product, product_sku='1',
                                 product_name='منتج', price=1000, quantity=3, line_total=3000)
        record_online_order_moves(order)

        product.refresh_from_db()
        self.assertEqual(product.quantity, 1)
        # الحاسبتان تريان الخصم عند أول مزامنة
        pulled = self.client.get('/api/pos/pull/?since=0', **self._auth(self.device_a)).json()
        reasons = [event['payload'].get('reason') for event in pulled['events']]
        self.assertIn('online_order', reasons)
        self.assertTrue(PosEvent.objects.filter(device_id='website').exists())

    def test_admin_only_products_keep_their_manual_quantity(self):
        """منتج مضاف من لوحة الإدارة بلا حركات لا تُصفَّر كميته."""
        from .models import Product
        from .pos_sync import recompute_product_quantity

        product = Product.objects.create(name='منتج إداري', sku='ADM', quantity=12)
        recompute_product_quantity(str(product.uuid))
        product.refresh_from_db()
        self.assertEqual(product.quantity, 12)


class LegacyEndpointsClosedTests(TestCase):
    """المسارات القديمة كانت محميّة برمز مشترك وُزّع داخل المُثبِّتات، وكانت
    تكشف أسعار الشراء وتسمح بتعديل المخزون. يجب أن تبقى مغلقة إلى الأبد."""

    CLOSED = [
        ('get', '/api/stock_snapshot/'),
        ('post', '/api/stock_update/'),
        ('post', '/api/sync/push/'),
        ('get', '/api/sync/pull/'),
        ('post', '/api/reserve/'),
    ]

    def test_legacy_write_endpoints_no_longer_exist(self):
        for method, path in self.CLOSED:
            response = getattr(self.client, method)(
                path, HTTP_AUTHORIZATION='Token any-old-shared-token')
            self.assertEqual(
                response.status_code, 404,
                f'{path} ما زال موجوداً — يجب حذفه لا حراسته')

    def test_public_product_api_hides_purchase_price(self):
        from .models import Product
        Product.objects.create(name='منتج', sku='1', buy_price=7500,
                               sell_price=10500, quantity=3, reviewed=True)
        body = self.client.get('/api/products/').content.decode()
        self.assertIn('10500', body)
        self.assertNotIn('7500', body)      # سعر الشراء لا يخرج للعلن

    def test_orders_count_requires_a_device_token(self):
        import secrets

        from .models import PosDevice
        self.assertEqual(self.client.get('/api/pos/orders_count/').status_code, 401)
        self.assertEqual(
            self.client.get('/api/pos/orders_count/',
                            HTTP_AUTHORIZATION='Token wrong').status_code, 401)

        device = PosDevice.objects.create(device_id='d', name='حاسبة',
                                          token=secrets.token_hex(16))
        response = self.client.get('/api/pos/orders_count/',
                                   HTTP_AUTHORIZATION=f'Token {device.token}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('pending_orders', response.json())


class UnifiedImageUploaderTests(TestCase):
    """رفع الصور من مكان واحد.

    تمرّ الاختبارات بمسار لوحة الإدارة الحقيقي: save(commit=False) ثم حفظ
    الكائن ثم save_model — لا باستدعاء save(commit=True) مباشرة، لأن ذلك
    لا يشبه ما يحدث فعلاً وقد يُخفي أخطاء.
    """

    def _save_through_admin(self, files, data=None, instance=None):
        from django.contrib import admin as django_admin
        from django.utils.datastructures import MultiValueDict

        payload = {
            'name': 'منتج', 'sku': '1', 'description': '',
            'specifications_text': '', 'buy_price': 1000, 'sell_price': 1500,
            'quantity': 4, 'is_offer': False, 'category': '',             'featured_priority': 0,
        }
        payload.update(data or {})
        multi = MultiValueDict()
        for key, value in payload.items():
            multi.setlist(key, value if isinstance(value, list) else [value])

        form = ProductAdminForm(multi, MultiValueDict({'product_images': list(files)}),
                                instance=instance)
        if not form.is_valid():
            return form, None

        product = form.save(commit=False)          # كما تفعل اللوحة
        model_admin = django_admin.site._registry[Product]
        model_admin.save_model(None, product, form, change=instance is not None)
        form.save_m2m()
        product.refresh_from_db()
        return form, product

    def test_first_upload_becomes_main_and_rest_go_to_gallery(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                form, product = self._save_through_admin(
                    [_uploaded_test_image(600, 600) for _ in range(4)])
                self.assertTrue(form.is_valid(), form.errors)
                self.assertTrue(product.image, 'الصورة الأولى لم تصبح رئيسية')
                self.assertEqual(product.gallery_images.count(), 3)

    def test_more_images_append_to_the_existing_ones(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                _, product = self._save_through_admin(
                    [_uploaded_test_image(600, 600) for _ in range(3)])
                form, product = self._save_through_admin(
                    [_uploaded_test_image(600, 600) for _ in range(2)], instance=product)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(1 + product.gallery_images.count(), 5)

    def test_uploading_past_the_limit_is_refused(self):
        from .models import MAX_PRODUCT_IMAGES

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                form, product = self._save_through_admin(
                    [_uploaded_test_image(400, 400)
                     for _ in range(MAX_PRODUCT_IMAGES + 1)])
                self.assertFalse(form.is_valid())
                self.assertIsNone(product)
                self.assertIn(str(MAX_PRODUCT_IMAGES), str(form.errors))

    def test_marked_images_are_deleted_on_save(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                _, product = self._save_through_admin(
                    [_uploaded_test_image(600, 600) for _ in range(3)])
                extra = product.gallery_images.first()

                form, product = self._save_through_admin(
                    [], data={'pi_remove': f'g{extra.pk}'}, instance=product)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(product.gallery_images.count(), 1)
                self.assertTrue(product.image, 'الرئيسية حُذفت بالخطأ')

    def test_removing_the_main_image_promotes_nothing_but_clears_it(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                _, product = self._save_through_admin(
                    [_uploaded_test_image(600, 600) for _ in range(2)])
                form, product = self._save_through_admin(
                    [], data={'pi_remove': 'main'}, instance=product)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertFalse(product.image, 'الرئيسية لم تُحذف')
                self.assertEqual(product.gallery_images.count(), 1)

    def test_non_image_upload_is_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        bad = SimpleUploadedFile('notes.txt', b'hello', content_type='text/plain')
        form, product = self._save_through_admin([bad])
        self.assertFalse(form.is_valid())
        self.assertIsNone(product)
        self.assertIn('ليس صورة', str(form.errors))


class CategoryCascadeTests(TestCase):
    """قوائم التصنيفات المتتابعة وإضافة تصنيف من داخل استمارة المنتج.

    تمرّ عبر عنوان اللوحة الحقيقي لا بالنداء المباشر على الدالة، لأن
    الصلاحيات و admin_view جزء من السلوك المطلوب فحصه.
    """

    def setUp(self):
        from django.contrib.auth.models import User
        from .models import Category

        self.url = reverse('admin:store_category_quick_add')
        self.boss = User.objects.create_superuser('boss', 'b@x.com', 'pw-12345678')
        self.clerk = User.objects.create_user('clerk', 'c@x.com', 'pw-12345678',
                                              is_staff=True)
        self.root = Category.objects.create(name='إلكترونيات')
        self.child = Category.objects.create(name='مقاومات', parent=self.root)

    def test_widget_shows_only_roots_and_the_selected_chain(self):
        from .admin import CategoryCascadeWidget

        html = CategoryCascadeWidget().render('category', str(self.child.pk))
        self.assertIn('cc-levels', html)
        self.assertIn(str(self.child.pk), html)
        # الشجرة كاملة تُمرَّر لجافاسكربت (مُهرَّبة داخل data-tree)
        self.assertIn('__roots__', html)
        tree = json.loads(unescape(
            html.split("data-tree='")[1].split("'\n")[0]))
        self.assertIn(str(self.root.pk), tree['__roots__'])
        self.assertNotIn(str(self.child.pk), tree['__roots__'])
        self.assertEqual(tree[str(self.root.pk)]['children'],
                         [str(self.child.pk)])

    def test_quick_add_creates_a_child_under_the_chosen_parent(self):
        from .models import Category

        self.client.force_login(self.boss)
        response = self.client.post(self.url, {'name': 'مكثفات',
                                               'parent': self.root.pk})
        body = response.json()

        self.assertTrue(body['ok'], body)
        created = Category.objects.get(pk=body['id'])
        self.assertEqual(created.parent, self.root)

    def test_quick_add_can_go_one_level_deeper_than_a_leaf(self):
        from .models import Category

        self.client.force_login(self.boss)
        body = self.client.post(self.url, {'name': 'كربونية',
                                           'parent': self.child.pk}).json()

        self.assertTrue(body['ok'], body)
        self.assertEqual(Category.objects.get(pk=body['id']).parent, self.child)

    def test_quick_add_creates_a_root_when_no_parent_is_sent(self):
        from .models import Category

        self.client.force_login(self.boss)
        body = self.client.post(self.url, {'name': 'أدوات'}).json()

        self.assertTrue(body['ok'], body)
        self.assertIsNone(Category.objects.get(pk=body['id']).parent)

    def test_duplicate_name_under_the_same_parent_is_refused(self):
        self.client.force_login(self.boss)
        body = self.client.post(self.url, {'name': 'مقاومات',
                                           'parent': self.root.pk}).json()

        self.assertFalse(body['ok'])
        self.assertIn('مسبقاً', body['error'])

    def test_staff_without_permission_cannot_add(self):
        from .models import Category

        self.client.force_login(self.clerk)
        response = self.client.post(self.url, {'name': 'تهريب'})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Category.objects.filter(name='تهريب').exists())

    def test_get_is_not_allowed(self):
        self.client.force_login(self.boss)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_chosen_category_is_saved_on_the_product(self):
        from django.contrib import admin as django_admin
        from django.utils.datastructures import MultiValueDict

        payload = MultiValueDict()
        for key, value in {'name': 'منتج', 'sku': 'CC-1', 'description': '',
                           'specifications_text': '', 'buy_price': 1000,
                           'sell_price': 1500, 'quantity': 2,                            'featured_priority': 0,
                           'category': str(self.child.pk)}.items():
            payload.setlist(key, [value])

        form = ProductAdminForm(payload, MultiValueDict())
        self.assertTrue(form.is_valid(), form.errors)
        product = form.save(commit=False)
        django_admin.site._registry[Product].save_model(None, product, form,
                                                        change=False)
        form.save_m2m()
        product.refresh_from_db()

        self.assertEqual(product.category, self.child)


class CategoryUnifiedTreeTests(TestCase):
    """مصدر واحد للتصنيفات: قائمة الثلاث خطوط، شريط التصفية، وصفحة الإدارة.

    الشجرة صارت بعمق حر، فالفحص هنا يبني ثلاثة مستويات ويتأكد أن كل واجهة
    تعرضها وأن التصفية تلتقط الأحفاد لا الأبناء فقط.
    """

    def setUp(self):
        from django.contrib.auth.models import User
        from .models import Category

        self.root = Category.objects.create(name='روبوتات')
        self.child = Category.objects.create(name='درونات', parent=self.root)
        self.grandchild = Category.objects.create(name='مراوح درون', parent=self.child)
        self.boss = User.objects.create_superuser('boss2', 'b2@x.com', 'pw-12345678')

        self.deep_product = Product.objects.create(
            name='مروحة كاربون', sku='DR-1', sell_price=5000, quantity=4,
            category=self.grandchild, reviewed=True)

    def test_choosing_a_root_shows_products_of_its_grandchildren(self):
        response = self.client.get('/', {'view': 'electronics',
                                         'category': self.root.pk})
        self.assertContains(response, 'مروحة كاربون')

    def test_descendant_ids_covers_every_level(self):
        ids = self.root.descendant_ids()
        self.assertEqual(set(ids),
                         {self.root.pk, self.child.pk, self.grandchild.pk})

    def test_drawer_menu_renders_the_third_level(self):
        response = self.client.get('/')
        self.assertContains(response, 'درونات')
        self.assertContains(response, 'مراوح درون')

    def test_full_path_shows_the_whole_chain(self):
        self.assertEqual(self.grandchild.full_path, 'روبوتات › درونات › مراوح درون')

    # ملفات static المضغوطة لا تُجمَّع في بيئة الاختبار، فنستعمل التخزين البسيط
    _plain_static = override_settings(
        STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')

    @_plain_static
    def test_admin_page_is_a_tree_with_counts(self):
        self.client.force_login(self.boss)
        response = self.client.get(reverse('admin:store_category_changelist'))

        self.assertTemplateUsed(response, 'admin/store/category_tree.html')
        self.assertContains(response, 'مراوح درون')
        self.assertContains(response, 'ct-tree')
        # المنتج محسوب على تصنيفه وعلى مجموع أجداده
        self.assertContains(response, '1 منتج')

    @_plain_static
    def test_admin_flat_view_still_available(self):
        self.client.force_login(self.boss)
        response = self.client.get(
            reverse('admin:store_category_changelist'), {'flat': '1'})

        self.assertTemplateNotUsed(response, 'admin/store/category_tree.html')

    def test_a_category_cannot_be_moved_under_its_own_branch(self):
        self.root.parent = self.grandchild
        with self.assertRaises(ValidationError):
            self.root.full_clean()

    def test_parent_chooser_hides_the_category_and_its_branch(self):
        from .admin import CategoryAdminForm

        html = CategoryAdminForm(instance=self.root)['parent'].as_widget()
        tree = json.loads(unescape(html.split("data-tree='")[1].split("'\n")[0]))

        self.assertNotIn(str(self.root.pk), tree)
        self.assertNotIn(str(self.grandchild.pk), tree)

    def test_series_is_gone(self):
        from django.apps import apps

        with self.assertRaises(LookupError):
            apps.get_model('store', 'Series')
        self.assertFalse(
            any(f.name == 'series' for f in Product._meta.get_fields()))


class ProductPricingTests(TestCase):
    def setUp(self):
        from .models import SiteSettings
        self.settings = SiteSettings.load()
        self.settings.usd_rate = 1700

    def test_product_shipping_pct_overrides_the_tier(self):
        product = Product(name='x', price_usd=1.0, shipping_pct=50)
        self.assertEqual(product.compute_prices(self.settings), (2550, 3500))
        product.shipping_pct = None  # 1$ تقع في الشريحة 2 → نقل 45%
        self.assertEqual(product.compute_prices(self.settings), (2450, 3500))

    def test_tiers_pick_shipping_and_profit_by_usd_price(self):
        s = self.settings
        self.assertEqual(s.tier_for(0.5), (50, 35))
        self.assertEqual(s.tier_for(2.99), (45, 35))
        self.assertEqual(s.tier_for(3), (40, 35))
        self.assertEqual(s.tier_for(25), (35, 35))
        s.tier3_max_usd, s.tier4_profit_pct = 20, 25
        self.assertEqual(s.tier_for(15), (40, 35))
        self.assertEqual(s.tier_for(25), (35, 25))
        product = Product(name='x', price_usd=25)
        self.assertEqual(product.compute_prices(s), (57400, 71750))

    def test_sell_rounds_up_50_until_500_then_250(self):
        r = self.settings.round_sell
        self.assertEqual([r(0), r(120), r(480), r(500), r(501), r(1000), r(1001)], [0, 150, 500, 500, 750, 1000, 1250])

    def test_offline_price_edit_locks_product_against_repricing(self):
        import uuid as U
        from . import pos_sync
        u = str(U.uuid4())
        p = Product.objects.create(name='x', uuid=u, price_usd=1.0, buy_price=2450, sell_price=3500)
        # نفس السعر من الأوفلاين → لا قفل
        pos_sync._apply_product({'uuid': u, 'name': 'x', 'sku': '', 'buy_price': 2450, 'sell_price': 3500,
                                 'updated_at': '2030-01-01T00:00:00.000Z'})
        p.refresh_from_db(); self.assertFalse(p.price_locked)
        # سعر جديد من الأوفلاين → يُقفل ويصعد للموقع
        pos_sync._apply_product({'uuid': u, 'name': 'x', 'sku': '', 'buy_price': 2450, 'sell_price': 4000,
                                 'updated_at': '2030-01-02T00:00:00.000Z'})
        p.refresh_from_db()
        self.assertTrue(p.price_locked); self.assertEqual(p.sell_price, 4000)
        self.assertIsNone(p.compute_prices(self.settings))
        self.settings.save()  # إعادة التسعير لا تلمسه
        p.refresh_from_db(); self.assertEqual(p.sell_price, 4000)

    def test_tier_bounds_must_ascend(self):
        from django.core.exceptions import ValidationError
        self.settings.tier2_max_usd = 0.5
        with self.assertRaises(ValidationError):
            self.settings.clean()

    def test_usd_from_buy_inverts_the_tier_formula(self):
        s = self.settings
        for usd in (0.4, 2.0, 5.0, 30.0):
            buy = usd * 1700 * (1 + s.tier_for(usd)[0] / 100.0)
            self.assertAlmostEqual(s.usd_from_buy(buy), usd, places=3)
        self.assertAlmostEqual(s.usd_from_buy(2550, 50), 1.0, places=3)

    def test_sell_floor_raises_but_never_lowers_the_sell_price(self):
        product = Product(name='x', price_usd=1.0, shipping_pct=50, sell_floor=5000)
        self.assertEqual(product.compute_prices(self.settings), (2550, 5000))
        product.sell_floor = 1000
        self.assertEqual(product.compute_prices(self.settings), (2550, 3500))


class OnlineOrderFlowTests(TestCase):
    """طلب الموقع: أجور التوصيل، قائمة البرنامج، التجهيز والإلغاء، والدردشة."""

    def setUp(self):
        import secrets

        from .models import Order, OrderItem, PosDevice, Product
        from .pos_sync import record_online_order_moves
        self.device = PosDevice.objects.create(device_id='dev', name='حاسبة',
                                               token=secrets.token_hex(16))
        self.product = Product.objects.create(name='أردوينو', sku='12', buy_price=5000,
                                              sell_price=8000, quantity=10)
        # رصيد افتتاحي كما في الواقع (كل منتج عنده حركات من البرنامج)
        from .models import StockMove
        StockMove.objects.create(uuid='open-1', product=self.product,
                                 product_uuid=str(self.product.uuid), delta=10, reason='opening')
        self.order = Order.objects.create(full_name='زبون تجريبي', phone='7701234567',
                                          province='بغداد', address='الكرادة', subtotal=16000,
                                          delivery_fee=6000, total=22000)
        OrderItem.objects.create(order=self.order, product=self.product, product_sku='12',
                                 product_name='أردوينو', price=8000, quantity=2, line_total=16000)
        record_online_order_moves(self.order)

    def _auth(self):
        return {'HTTP_AUTHORIZATION': f'Token {self.device.token}'}

    def _push(self, op):
        import uuid as uuid_module
        event = {'uuid': str(uuid_module.uuid4()), 'entity': 'online_order', 'op': op,
                 'entity_uuid': str(self.order.uuid), 'created_at': '2026-11-19T10:00:00.000Z',
                 'payload': {'order_uuid': str(self.order.uuid), 'receipt_no': 'A-9'}}
        return self.client.post('/api/pos/push/', data=json.dumps({'events': [event]}),
                                content_type='application/json', **self._auth())

    def test_delivery_fee_default_is_6000(self):
        from .models import SiteSettings
        self.assertEqual(SiteSettings.load().delivery_fee, 6000)

    def test_orders_endpoint_lists_items_and_totals(self):
        data = self.client.get('/api/pos/orders/', **self._auth()).json()
        self.assertEqual(len(data['orders']), 1)
        order = data['orders'][0]
        self.assertEqual(order['delivery_fee'], 6000)
        self.assertEqual(order['total'], 22000)
        self.assertEqual(order['items'][0]['product_uuid'], str(self.product.uuid))
        self.assertEqual(order['items'][0]['qty'], 2)

    def test_prepare_event_marks_order_prepared_and_hides_it(self):
        self.assertEqual(self._push('prepare').json()['accepted'].__len__(), 1)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'prepared')
        self.assertEqual(self.order.pos_receipt_no, 'A-9')
        self.assertEqual(self.client.get('/api/pos/orders/', **self._auth()).json()['orders'], [])
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 8)      # التجهيز لا يخصم مرة ثانية

    def test_cancel_event_returns_stock_once(self):
        self._push('cancel')
        self._push('cancel')
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')
        self.assertEqual(self.product.quantity, 10)

    def _login_as_owner(self):
        session = self.client.session
        session['customer_phone'] = self.order.phone
        session.save()

    def test_customer_sees_order_details(self):
        self._login_as_owner()
        r = self.client.get(f'/order/{self.order.id}/')
        self.assertContains(r, 'أردوينو')
        self.assertContains(r, 'إلغاء الطلب')
        self.assertContains(r, f'/order/{self.order.id}/')
        self.assertContains(self.client.get('/account/'), f'/order/{self.order.id}/')

    def test_stranger_cannot_view_or_cancel(self):
        session = self.client.session
        session['customer_phone'] = '7709999999'
        session.save()
        self.assertEqual(self.client.get(f'/order/{self.order.id}/').status_code, 302)
        self.client.post(f'/order/{self.order.id}/cancel/', {'reason': 'غيّرت رأيي'})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')

    def test_customer_cancel_returns_stock_and_hides_from_pos(self):
        self._login_as_owner()
        self.client.post(f'/order/{self.order.id}/cancel/', {'reason': 'غيّرت رأيي', 'other': 'لاحقاً'})
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')
        self.assertEqual(self.order.cancelled_by, 'customer')
        self.assertEqual(self.order.cancel_reason, 'غيّرت رأيي: لاحقاً')
        self.assertEqual(self.product.quantity, 10)
        self.assertEqual(self.client.get('/api/pos/orders/', **self._auth()).json()['orders'], [])
        # إلغاء ثانٍ لا يُرجع المخزون مرتين
        self.client.post(f'/order/{self.order.id}/cancel/', {'reason': 'غيّرت رأيي'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

    def test_prepared_order_cannot_be_cancelled_by_customer(self):
        self._push('prepare')
        self._login_as_owner()
        r = self.client.get(f'/order/{self.order.id}/')
        self.assertNotContains(r, 'تأكيد الإلغاء')
        self.client.post(f'/order/{self.order.id}/cancel/', {'reason': 'غيّرت رأيي'})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'prepared')

    def test_receipt_after_customer_cancel_deducts_again(self):
        """الزبون ألغى بينما البرنامج يجهّز وصدر وصل: المواد خرجت فعلاً."""
        self._login_as_owner()
        self.client.post(f'/order/{self.order.id}/cancel/', {'reason': 'غيّرت رأيي'})
        self._push('prepare')
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, 'prepared')
        self.assertEqual(self.product.quantity, 8)
        # إلغاء لاحق من الإدارة بعد إرجاعه للانتظار يُرجع الكمية مرة واحدة فقط
        from .pos_sync import release_online_order_moves
        from .models import Order
        Order.objects.filter(pk=self.order.pk).update(status='cancelled')
        self.order.refresh_from_db()
        release_online_order_moves(self.order)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

    def test_reorder_fills_the_cart(self):
        from .models import Product
        Product.objects.filter(pk=self.product.pk).update(reviewed=True)
        self._login_as_owner()
        r = self.client.post(f'/order/{self.order.id}/reorder/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.session['cart'], {str(self.product.id): {'qty': 2}})

    def test_chat_send_and_poll(self):
        r = self.client.post('/chat/send/', data=json.dumps({'text': 'هل المنتج متوفر؟', 'page': '/'}),
                             content_type='application/json', HTTP_HOST='localhost')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()['messages']), 2)   # الرسالة + الرد الآلي
        state = self.client.get('/chat/state/', {'after': 0, 'open': '1'}, HTTP_HOST='localhost').json()
        self.assertTrue(state['thread'])
        self.assertEqual(state['messages'][0]['text'], 'هل المنتج متوفر؟')


class MobilePosTests(TestCase):
    """البيع من الهاتف يكتب أحداث البرنامج نفسها ويخصم المخزون."""

    def setUp(self):
        from django.contrib.auth.models import User
        from .models import MobilePosProfile, StockMove
        self.user = User.objects.create_user('pos_test', password='x-test-pass', is_staff=True)
        self.profile = MobilePosProfile.objects.create(user=self.user, pos_username='انور',
                                                       receipt_prefix='AP')
        self.p1 = Product.objects.create(name='Hidden part', sku='12', sell_price=1500,
                                         buy_price=900, quantity=0, reviewed=False)
        self.p2 = Product.objects.create(name='Visible part', sku='55', sell_price=250,
                                         buy_price=100, quantity=0, reviewed=True)
        for p, q in ((self.p1, 3), (self.p2, 10)):
            StockMove.objects.create(uuid=f'mv-{p.pk}', product=p, product_uuid=str(p.uuid),
                                     delta=q, reason='adjust', created_at='2026-01-01T00:00:00.000Z')
            Product.objects.filter(pk=p.pk).update(quantity=q)
        self.client.force_login(self.user)

    def _post(self, url, body):
        return self.client.post(url, data=json.dumps(body), content_type='application/json')

    def test_requires_profile(self):
        from django.contrib.auth.models import User
        other = User.objects.create_user('np', password='x-test-pass', is_staff=True)
        self.client.force_login(other)
        self.assertEqual(self.client.get('/pos/').status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get('/pos/').status_code, 302)

    def test_products_include_hidden(self):
        data = self.client.get('/pos/api/products/').json()
        names = {p['n'] for p in data['products']}
        self.assertIn('Hidden part', names)
        self.assertNotIn('buy_price', json.dumps(data))

    def test_sale_writes_offline_events(self):
        from .models import PosEvent
        r = self._post('/pos/api/sale/', {'buyer': 'زبون', 'phone': '+964 781 545 3320',
                                           'discount': 250, 'items': [
                                               {'u': str(self.p1.uuid), 'q': 2, 'p': 1500},
                                               {'u': str(self.p2.uuid), 'q': 1, 'p': 250}]})
        d = r.json()
        self.assertTrue(d['ok'], d)
        self.assertEqual(d['receipt_no'], 'AP-1')
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.quantity, 1)
        sale = PosEvent.objects.get(entity='sale')
        self.assertEqual(sale.device_id, self.profile.device_id)
        self.assertEqual(sale.user_name, 'انور')
        p = sale.payload
        self.assertEqual(p['total'], 3250.0)
        self.assertEqual(p['discount'], 250.0)
        self.assertEqual(p['phone'], '07815453320')
        self.assertEqual({i['quantity'] for i in p['items']}, {2, 1})
        moves = PosEvent.objects.filter(entity='stock_move', device_id=self.profile.device_id)
        self.assertEqual(sorted(m.payload['delta'] for m in moves), [-2, -1])
        self.assertTrue(all(m.payload['ref_uuid'] == p['uuid'] for m in moves))
        page = self.client.get(f"/pos/receipt/{p['uuid']}/")
        self.assertContains(page, 'AP-1')
        self.assertContains(page, '3,000.00 د.ع')
        sales = self.client.get('/pos/api/sales/').json()['sales']
        self.assertEqual(sales[0]['no'], 'AP-1')
        self.assertEqual(sales[0]['net'], 3000.0)
        d2 = self._post('/pos/api/sale/', {'items': [{'u': str(self.p2.uuid), 'q': 1, 'p': 250}]}).json()
        self.assertEqual(d2['receipt_no'], 'AP-2')

    def test_oversell_rejected(self):
        from .models import PosEvent
        r = self._post('/pos/api/sale/', {'items': [{'u': str(self.p1.uuid), 'q': 4, 'p': 1500}]})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(PosEvent.objects.exists())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.last_receipt_no, 0)

    def test_deleted_sale_hidden(self):
        from .models import PosEvent
        d = self._post('/pos/api/sale/', {'items': [{'u': str(self.p2.uuid), 'q': 1, 'p': 250}]}).json()
        PosEvent.objects.create(uuid='del-1', entity='sale', entity_uuid=d['uuid'], op='delete',
                                payload={'uuid': d['uuid'], 'deleted_at': 'x'}, device_id='pc')
        self.assertEqual(self.client.get('/pos/api/sales/').json()['sales'], [])

    def test_project_add_update_payment(self):
        from .models import PosEvent
        d = self._post('/pos/api/projects/save/', {'name': 'مشروع تخرج', 'person': 'علي',
                                                    'practical_price': '200,000', 'materials_cost': 80000,
                                                    'theory_price': 100000, 'theory_share_pct': ''}).json()
        self.assertTrue(d['ok'])
        ev = PosEvent.objects.get(entity='project')
        for key in ('name', 'person', 'phone', 'practical_details', 'practical_price', 'materials_cost',
                    'theory_details', 'theory_price', 'theory_owner', 'theory_share_pct', 'note',
                    'status', 'year', 'archived_at', 'uuid', 'device_id', 'created_at',
                    'updated_at', 'deleted_at'):
            self.assertIn(key, ev.payload)
        self.assertEqual(ev.payload['theory_share_pct'], 80.0)
        self.assertEqual(ev.payload['status'], 'open')
        r = self._post('/pos/api/projects/payment/', {'project_uuid': d['uuid'], 'kind': 'client',
                                                       'amount': 150000, 'date': '2026-11-21'}).json()
        self.assertTrue(r['ok'])
        self._post('/pos/api/projects/save/', {'uuid': d['uuid'], 'name': 'مشروع تخرج 2',
                                                'practical_price': 200000, 'materials_cost': 80000,
                                                'theory_price': 100000, 'theory_share_pct': 80})
        projects = self.client.get('/pos/api/projects/').json()['projects']
        self.assertEqual(len(projects), 1)
        pj = projects[0]
        self.assertEqual(pj['name'], 'مشروع تخرج 2')
        self.assertEqual(pj['fin']['total_fees'], 300000)
        self.assertEqual(pj['fin']['client_remaining'], 150000)
        self.assertEqual(pj['fin']['our_income'], 140000)  # 120000 ربح عملي + 20000 حصتنا
        self.assertEqual(PosEvent.objects.filter(entity='project', op='update').count(), 1)

    def test_seller_and_editable_date(self):
        d = self._post('/pos/api/sale/', {'date': '2026-11-20T09:30',
                                           'items': [{'u': str(self.p2.uuid), 'q': 1, 'p': 250}]}).json()
        row = self.client.get('/pos/api/sales/').json()['sales'][0]
        self.assertEqual(row['date'], '2026-11-20 09:30')
        self.assertEqual(row['seller'], 'انور · هاتف انور')
        page = self.client.get(f"/pos/receipt/{d['uuid']}/")
        self.assertContains(page, 'هاتف انور')
        self.assertContains(page, '2026-11-20 09:30')
        home = self.client.get('/pos/')
        self.assertContains(home, 'AP-2')
        # تاريخ غير صالح → الآن
        d2 = self._post('/pos/api/sale/', {'date': 'xx', 'items': [{'u': str(self.p2.uuid), 'q': 1, 'p': 250}]})
        self.assertTrue(d2.json()['ok'])

    def test_project_duration_and_first_payment(self):
        from .models import PosEvent
        d = self._post('/pos/api/projects/save/', {'name': 'p', 'duration': 'أسبوعان',
                                                    'practical_price': 100000, 'first_pay': 30000}).json()
        ev = PosEvent.objects.get(entity='project')
        self.assertEqual(ev.payload['duration'], 'أسبوعان')
        pay = PosEvent.objects.get(entity='project_payment')
        self.assertEqual(pay.payload['amount'], 30000.0)
        self.assertEqual(pay.payload['note'], 'دفعة أولى')
        pj = self.client.get('/pos/api/projects/').json()['projects'][0]
        self.assertEqual(pj['duration'], 'أسبوعان')
        self.assertEqual(pj['fin']['client_remaining'], 70000)
        # التعديل لا يضيف دفعة أولى ثانية
        self._post('/pos/api/projects/save/', {'uuid': d['uuid'], 'name': 'p', 'first_pay': 5})
        self.assertEqual(PosEvent.objects.filter(entity='project_payment').count(), 1)
