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
