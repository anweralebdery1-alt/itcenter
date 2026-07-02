import io
import logging
import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from .image_processing import prepare_product_image


logger = logging.getLogger(__name__)

try:
    from PIL import Image
except Exception:  # Pillow غير متوفر → نتجاوز الضغط بهدوء
    Image = None


def _compress_imagefield(field_file, max_dim=1200, quality=82):
    """يصغّر ويضغط الصورة ليكون الموقع أخف على الزبائن.
    يُعيد (buffer, ext) أو None عند الفشل."""
    if Image is None:
        return None
    try:
        field_file.seek(0)
        img = Image.open(field_file)
        img.load()
    except Exception:
        return None

    has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    buffer = io.BytesIO()
    if has_alpha:
        # نُبقي الشفافية → PNG مُحسّن
        img.convert('RGBA').save(buffer, format='PNG', optimize=True)
        ext = 'png'
    else:
        img.convert('RGB').save(buffer, format='JPEG', quality=quality, optimize=True, progressive=True)
        ext = 'jpg'
    buffer.seek(0)
    return buffer, ext


class ImageCompressMixin(models.Model):
    """يضغط حقول الصور تلقائياً عند رفع ملف جديد فقط (لا يلمس صوراً موجودة)."""
    image_fields = ('image',)

    class Meta:
        abstract = True

    def process_image_field(self, field_name, field_file):
        return _compress_imagefield(field_file)

    def save(self, *args, **kwargs):
        for fname in self.image_fields:
            f = getattr(self, fname, None)
            # نضغط فقط الملفات المرفوعة حديثاً (غير المحفوظة بعد في التخزين)
            if f and not getattr(f, '_committed', True):
                result = self.process_image_field(fname, f)
                if result:
                    buffer, ext = result
                    base = os.path.splitext(os.path.basename(f.name))[0]
                    f.save(f"{base}.{ext}", ContentFile(buffer.read()), save=False)
        super().save(*args, **kwargs)
class Category(models.Model):
    name = models.CharField(max_length=200)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    def __str__(self): return self.name
class Series(models.Model):
    name = models.CharField(max_length=200)
    def __str__(self): return self.name

class SiteSettings(ImageCompressMixin, models.Model):
    image_fields = ('logo', 'hero_image')
    site_name = models.CharField(max_length=200, default='متجر المكونات')
    tagline = models.CharField(max_length=300, default='كل ما تحتاجه من قطع ومستلزمات إلكترونية')
    hero_title = models.CharField(max_length=300, default='مكونات إلكترونية جاهزة للطلب')
    hero_subtitle = models.TextField(default='تصفح المنتجات المتوفرة في المخزن واطلبها بنظام الدفع عند الاستلام.')
    phone = models.CharField(max_length=50, blank=True)
    whatsapp = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=300, blank=True)
    logo = models.ImageField(upload_to='site/', blank=True, null=True)
    hero_image = models.ImageField(upload_to='site/', blank=True, null=True)
    primary_color = models.CharField(max_length=20, default='#0B4EA2')
    accent_color = models.CharField(max_length=20, default='#FF8A00')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'إعدادات الموقع'
        verbose_name_plural = 'إعدادات الموقع'

    def __str__(self):
        return self.site_name

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class Product(ImageCompressMixin, models.Model):
    image_fields = ('image',)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    # معرف المنتج في برنامج الأوفلاين = مفتاح المزامنة الفريد (يسمح بتكرار الـSKU)
    local_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    sku = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    buy_price = models.FloatField(default=0)
    sell_price = models.FloatField(default=0)
    quantity = models.IntegerField(default=0)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    series = models.ForeignKey(Series, null=True, blank=True, on_delete=models.SET_NULL)
    is_offer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def process_image_field(self, field_name, field_file):
        if field_name == 'image':
            try:
                return prepare_product_image(field_file)
            except Exception:
                logger.exception('Failed to add branding to product image')
                return _compress_imagefield(field_file)
        return super().process_image_field(field_name, field_file)

    def __str__(self): return self.name


class ProductImage(ImageCompressMixin, models.Model):
    image_fields = ('image',)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='gallery_images',
    )
    image = models.ImageField(upload_to='products/gallery/')
    position = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
    )
    alt_text = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('position', 'id')
        verbose_name = 'صورة إضافية للمنتج'
        verbose_name_plural = 'صور المنتج الإضافية'

    def clean(self):
        super().clean()
        if self.product_id:
            existing = ProductImage.objects.filter(product_id=self.product_id)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.count() >= 4:
                raise ValidationError(
                    'يمكن إضافة أربع صور إضافية فقط، ليكون الإجمالي خمس صور.'
                )

    def process_image_field(self, field_name, field_file):
        if field_name == 'image':
            try:
                return prepare_product_image(field_file)
            except Exception:
                logger.exception('Failed to add branding to gallery image')
                return _compress_imagefield(field_file)
        return super().process_image_field(field_name, field_file)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product} - صورة {self.position}'


class Customer(models.Model):
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL)
    phone = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    province = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or self.phone


class PhoneOTP(models.Model):
    phone = models.CharField(max_length=50)
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.created_at + timezone.timedelta(minutes=10)

    def __str__(self):
        return f"{self.phone} - {self.code}"


class Order(models.Model):
    PAYMENT_CHOICES = [('cod', 'الدفع عند الاستلام'), ('card', 'دفع إلكتروني')]
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('confirmed', 'مؤكد'),
        ('paid', 'مدفوع'),
        ('cancelled', 'ملغي'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    province = models.CharField(max_length=100)
    address = models.TextField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cod')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.phone}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    product_sku = models.CharField(max_length=100)
    product_name = models.CharField(max_length=300)
    price = models.FloatField(default=0)
    quantity = models.IntegerField(default=1)
    line_total = models.FloatField(default=0)

    def __str__(self):
        return self.product_name

class SiteSection(ImageCompressMixin, models.Model):
    image_fields = ('image',)
    SECTION_TYPES = [
        ('electronics', 'قسم الإلكترونيات'),
        ('courses', 'الدورات التدريبية'),
        ('videos', 'فيديوهات تعليمية'),
        ('about', 'حول المركز'),
        ('custom', 'بطاقة مخصصة'),
    ]
    title = models.CharField(max_length=200)
    section_type = models.CharField(max_length=30, choices=SECTION_TYPES, default='custom')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='sections/', blank=True, null=True)
    url = models.CharField(max_length=300, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title


class Course(ImageCompressMixin, models.Model):
    image_fields = ('image',)
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='courses/', blank=True, null=True)
    price = models.FloatField(default=0)
    duration = models.CharField(max_length=100, blank=True)
    trainer = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class EducationalVideo(ImageCompressMixin, models.Model):
    image_fields = ('thumbnail',)
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    thumbnail = models.ImageField(upload_to='videos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class DownloadableFile(models.Model):
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='downloads/')
    video = models.ForeignKey(EducationalVideo, null=True, blank=True, on_delete=models.CASCADE, related_name='files')
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.CASCADE, related_name='files')
    is_free = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TeamMember(ImageCompressMixin, models.Model):
    image_fields = ('image',)
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    image = models.ImageField(upload_to='team/', blank=True, null=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

class SaleReservation(models.Model):
    STATUS_CHOICES = [('reserved','reserved'),('processed','processed')]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    items = models.JSONField()  # list of {product_sku, qty, price}
    total = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reserved')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Reservation {self.uuid} — {self.full_name}"
