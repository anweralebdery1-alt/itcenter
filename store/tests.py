import io
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
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
        )
        Product.objects.create(
            name="Unavailable product",
            sku="UNAVAILABLE",
            sell_price=1000,
            quantity=0,
        )

        home_response = self.client.get("/")
        self.assertContains(home_response, "● متوفر")
        self.assertContains(home_response, "● غير متوفر")
        self.assertNotContains(home_response, "متوفر 37")

        detail_response = self.client.get(f"/product/{available.pk}/")
        self.assertContains(detail_response, ">متوفر</span>", html=False)
        self.assertNotContains(detail_response, "متوفر في المخزن")


class ProductGalleryTests(TestCase):
    def test_four_optional_images_are_allowed_and_fifth_is_rejected(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                product = Product.objects.create(
                    name="Gallery product",
                    sku="GALLERY",
                    sell_price=1000,
                    quantity=5,
                    image=_uploaded_test_image(800, 800),
                )
                for position in range(1, 5):
                    ProductImage.objects.create(
                        product=product,
                        image=_uploaded_test_image(800, 800),
                        position=position,
                    )

                self.assertEqual(product.gallery_images.count(), 4)
                first_gallery_image = product.gallery_images.first()
                with Image.open(first_gallery_image.image.path) as image:
                    self.assertEqual(image.size, (CANVAS_SIZE, CANVAS_SIZE))

                response = self.client.get(f"/product/{product.pk}/")
                self.assertEqual(response.content.count(b'data-image='), 5)

                with self.assertRaises(ValidationError):
                    ProductImage.objects.create(
                        product=product,
                        image=_uploaded_test_image(800, 800),
                        position=4,
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
                'series': '',
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
                'series': '',
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
