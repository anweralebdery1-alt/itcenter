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
    order = models.IntegerField(default=0, blank=True, verbose_name='أولوية الظهور',
                                help_text='الأصغر يظهر أولاً في شريط التصنيفات.')
    is_active = models.BooleanField(default=True, verbose_name='مفعّل')

    class Meta:
        ordering = ('order', 'name')
        verbose_name = 'تصنيف'
        verbose_name_plural = 'التصنيفات'

    def __str__(self):
        return self.full_path

    @property
    def full_path(self):
        """المسار كاملاً: «الأب › الابن › الحفيد» مهما تعمّق."""
        names = [self.name]
        node = self
        seen = {self.pk}
        while node.parent_id and node.parent_id not in seen:
            seen.add(node.parent_id)
            node = node.parent
            names.append(node.name)
        return ' › '.join(reversed(names))

    def ancestor_ids(self):
        """معرّفات الآباء من الأقرب إلى الجذر."""
        ids = []
        node = self
        while node.parent_id and node.parent_id not in ids and node.parent_id != self.pk:
            ids.append(node.parent_id)
            node = node.parent
        return ids

    def descendant_ids(self):
        """معرّف هذا التصنيف وكل ما تحته مهما تعمّق (للتصفية في المتجر)."""
        ids = [self.pk]
        frontier = [self.pk]
        while frontier:
            children = list(
                Category.objects.filter(parent_id__in=frontier)
                .exclude(pk__in=ids)
                .values_list('id', flat=True)
            )
            if not children:
                break
            ids.extend(children)
            frontier = children
        return ids

    def clean(self):
        """يمنع أن يصير التصنيف أباً لنفسه أو لأحد آبائه — حلقة تُجمّد الشجرة."""
        if self.parent_id and self.pk:
            if self.parent_id == self.pk:
                raise ValidationError({'parent': 'لا يمكن أن يكون التصنيف أباً لنفسه.'})
            if self.pk in Category.objects.get(pk=self.parent_id).ancestor_ids():
                raise ValidationError(
                    {'parent': 'لا يمكن نقل التصنيف تحت أحد فروعه.'})

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
    meta_description = models.CharField(
        max_length=300, blank=True, verbose_name='وصف الموقع لمحركات البحث (Meta Description)',
        help_text='وصف مختصر (حتى 160 حرفاً) يظهر في نتائج بحث جوجل للصفحة الرئيسية.')
    meta_keywords = models.CharField(
        max_length=300, blank=True, verbose_name='كلمات مفتاحية',
        help_text='كلمات يفصل بينها فاصلة، مثل: أردوينو, حسّاسات, روبوت, قطع إلكترونية.')
    google_site_verification = models.CharField(
        max_length=200, blank=True, verbose_name='رمز التحقق من Google Search Console',
        help_text='الصق قيمة "content" من وسم التحقق google-site-verification فقط.')
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

    @property
    def whatsapp_intl(self):
        """رقم واتساب بصيغة دولية (9647...) من حقل واتساب فقط (لا يرجع لحقل الهاتف).
        يقتطع أول رقم إن احتوى الحقل أكثر من رقم — أرقام العراق: 10 خانات محلية تبدأ بـ7."""
        d = ''.join(ch for ch in (self.whatsapp or '') if ch.isdigit())
        if not d:
            return ''
        if d.startswith('964'):
            d = d[:13]        # 964 + 10 خانات
        elif d.startswith('0'):
            d = d[1:11]       # أزل الصفر ثم خذ 10 خانات
        else:
            d = d[:10]
        return d if d.startswith('964') else '964' + d


class ProductQuerySet(models.QuerySet):
    def visible(self):
        """المنتجات التي يراها الزبون — تستثني ما حُذف من نقطة البيع."""
        return self.filter(deleted_at__isnull=True)


class Product(ImageCompressMixin, models.Model):
    image_fields = ('image',)
    objects = ProductQuerySet.as_manager()
    # مفتاح المزامنة الموحّد بين الموقع والحاسبتين — يسمح بتكرار الـSKU
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    # معرف المنتج في برنامج الأوفلاين (المزامنة القديمة) — يبقى للتوافق فقط
    local_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)
    # حذف منطقي: المنتج المحذوف من نقطة البيع يختفي من المتجر ولا يُمسح صفّه،
    # وإلا عاد من جديد عند أول مزامنة من الحاسبة الأخرى.
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='تاريخ الحذف')
    # طابع آخر تعديل كما أرسلته نقطة البيع — يُستخدم لحسم التعارض (الأحدث يفوز)
    pos_updated_at = models.CharField(max_length=40, blank=True, editable=False)
    sku = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    # نسخة مصغّرة خفيفة جداً للعرض في قوائم المنتجات (تُولَّد تلقائياً)
    thumbnail = models.ImageField(upload_to='products/thumbs/', blank=True, null=True, editable=False)
    buy_price = models.FloatField(default=0)
    sell_price = models.FloatField(default=0)
    quantity = models.IntegerField(default=0)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    is_offer = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, verbose_name='منتج مميّز')
    featured_priority = models.IntegerField(default=0, blank=True, verbose_name='أولوية الظهور',
                                            help_text='الأعلى يظهر أولاً بين المنتجات المميّزة')
    views_count = models.PositiveIntegerField(default=0, verbose_name='عدد المشاهدات')
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

    def save(self, *args, **kwargs):
        img = getattr(self, 'image', None)
        new_image = bool(img) and not getattr(img, '_committed', True)
        if new_image:
            self.thumbnail = None  # صورة جديدة → أعد توليد المصغّرة
        super().save(*args, **kwargs)
        self._ensure_thumbnail()

    def _ensure_thumbnail(self):
        """يولّد نسخة مصغّرة خفيفة جداً من الصورة الرئيسية إن لم تكن موجودة."""
        if not self.image or self.thumbnail:
            return
        try:
            self.image.open('rb')
            result = _compress_imagefield(self.image, max_dim=430, quality=62)
        except Exception:
            logger.exception('thumbnail generation failed')
            return
        finally:
            try:
                self.image.close()
            except Exception:
                pass
        if not result:
            return
        buffer, ext = result
        base = os.path.splitext(os.path.basename(self.image.name))[0]
        self.thumbnail.save(f"{base}-thumb.{ext}", ContentFile(buffer.read()), save=False)
        super().save(update_fields=['thumbnail'])

    @property
    def list_image_url(self):
        """رابط الصورة الخفيفة للقوائم (المصغّرة إن وُجدت وإلا الأصلية)."""
        if self.thumbnail:
            return self.thumbnail.url
        if self.image:
            return self.image.url
        return ''

    def __str__(self): return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('product_detail', args=[self.pk])

    @property
    def meta_description(self):
        text = (self.description or '').strip()
        if not text:
            text = self.name
        text = ' '.join(text.split())
        return text[:160]


# أقصى عدد صور للمنتج: الرئيسية + الباقي في المعرض
MAX_PRODUCT_IMAGES = 10
MAX_GALLERY_IMAGES = MAX_PRODUCT_IMAGES - 1


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
        validators=[MinValueValidator(1), MaxValueValidator(MAX_GALLERY_IMAGES)],
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
            if existing.count() >= MAX_GALLERY_IMAGES:
                raise ValidationError(
                    f'الحد الأقصى {MAX_PRODUCT_IMAGES} صور للمنتج الواحد.'
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


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    name = models.CharField(max_length=120, verbose_name='الاسم')
    phone = models.CharField(max_length=50, blank=True, verbose_name='هاتف المقيّم')
    rating = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name='التقييم (نجوم)')
    comment = models.TextField(blank=True, verbose_name='التعليق')
    is_approved = models.BooleanField(default=True, verbose_name='معتمَد للنشر')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'تقييم'
        verbose_name_plural = 'التقييمات'

    def __str__(self):
        return f'{self.product} - {self.rating}★ - {self.name}'


class PushSubscription(models.Model):
    """اشتراك إشعارات ويب لجهاز الأدمن (المثبِّت للموقع كتطبيق)."""
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    label = models.CharField(max_length=120, blank=True, verbose_name='الجهاز/الاسم')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'اشتراك إشعارات'
        verbose_name_plural = 'اشتراكات الإشعارات'

    def __str__(self):
        return self.label or self.endpoint[:40]


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
    components = models.TextField(blank=True, verbose_name='المكوّنات المطلوبة',
                                 help_text='اكتب مكوّناً في كل سطر.')
    wiring = models.TextField(blank=True, verbose_name='طريقة التوصيل',
                             help_text='كل توصيلة في سطر، مثل: طرف الحسّاس Trig ← الطرف 9.')
    code = models.TextField(blank=True, verbose_name='الكود (Arduino)')
    source = models.CharField(max_length=300, blank=True, verbose_name='المصدر',
                              help_text='اسم صاحب الفيديو/المصدر (للأمانة).')
    project_number = models.IntegerField(default=0, verbose_name='رقم المشروع',
                                        help_text='رقم متسلسل لتسهيل البحث عن المشروع.')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('project_number', 'id')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('video_detail', args=[self.pk])

    @property
    def youtube_id(self):
        import re
        m = re.search(r'(?:v=|youtu\.be/|/embed/|/shorts/|/live/)([A-Za-z0-9_-]{11})', self.video_url or '')
        return m.group(1) if m else ''

    @property
    def youtube_embed_url(self):
        vid = self.youtube_id
        return f'https://www.youtube.com/embed/{vid}' if vid else ''

    @property
    def components_list(self):
        return [line.strip() for line in (self.components or '').splitlines() if line.strip()]

    @property
    def wiring_list(self):
        return [line.strip() for line in (self.wiring or '').splitlines() if line.strip()]

    @property
    def thumbnail_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        if self.youtube_id:
            return f'https://img.youtube.com/vi/{self.youtube_id}/hqdefault.jpg'
        return ''


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

class PosDevice(models.Model):
    """حاسبة نقطة بيع مصرّح لها بالمزامنة. لكل جهاز رمزه الخاص ليمكن إيقافه وحده."""
    device_id = models.CharField(max_length=64, unique=True, verbose_name='معرّف الجهاز')
    name = models.CharField(max_length=100, verbose_name='الاسم', help_text='مثل: حاسبة أنور')
    token = models.CharField(max_length=64, unique=True, verbose_name='رمز الاتصال')
    is_active = models.BooleanField(default=True, verbose_name='مفعّل')
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name='آخر اتصال')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'جهاز نقطة بيع'
        verbose_name_plural = 'أجهزة نقاط البيع'

    def __str__(self):
        return self.name or self.device_id


class AppRelease(models.Model):
    """إصدار من برنامج نقطة البيع. ترفع ملف MSI هنا، فتكتشفه الحاسبات
    تلقائياً عند التشغيل وتعرض على المستخدم زر تحديث."""
    version = models.CharField(max_length=20, unique=True, verbose_name='رقم الإصدار',
                               help_text='مثل 1.3.2 — أرقام يفصلها نقاط')
    installer = models.FileField(upload_to='releases/', verbose_name='ملف التنصيب (MSI)')
    notes = models.TextField(blank=True, verbose_name='ما الجديد',
                             help_text='يظهر للمستخدم في نافذة التحديث. سطر لكل تغيير.')
    is_active = models.BooleanField(default=True, verbose_name='منشور',
                                    help_text='أزل العلامة لإيقاف توزيع هذا الإصدار فوراً.')
    is_mandatory = models.BooleanField(default=False, verbose_name='تحديث إلزامي',
                                       help_text='يُطلب التحديث بإلحاح ولا يُسمح بتأجيله.')
    sha256 = models.CharField(max_length=64, blank=True, editable=False,
                              verbose_name='بصمة الملف')
    size_bytes = models.BigIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'إصدار البرنامج'
        verbose_name_plural = 'إصدارات البرنامج'

    def __str__(self):
        return f'v{self.version}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # نحسب البصمة بعد الحفظ ليكون الملف على القرص — بها تتأكد الحاسبة
        # أن ما نزّلته سليم وغير مبتور قبل تشغيله.
        if self.installer and not self.sha256:
            import hashlib
            digest = hashlib.sha256()
            size = 0
            self.installer.open('rb')
            try:
                for block in iter(lambda: self.installer.read(1024 * 1024), b''):
                    digest.update(block)
                    size += len(block)
            finally:
                self.installer.close()
            AppRelease.objects.filter(pk=self.pk).update(
                sha256=digest.hexdigest(), size_bytes=size)
            self.sha256 = digest.hexdigest()
            self.size_bytes = size

    @property
    def version_tuple(self):
        parts = []
        for chunk in str(self.version or '').split('.'):
            digits = ''.join(ch for ch in chunk if ch.isdigit())
            parts.append(int(digits) if digits else 0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])


class PosEvent(models.Model):
    """سجل المزامنة المركزي: كل تغيير حصل على أي حاسبة يُخزَّن هنا مرة واحدة،
    وتسحبه الحاسبة الأخرى بالترتيب. هذا السجل هو مصدر الحقيقة الكامل للنظام."""
    seq = models.AutoField(primary_key=True)
    uuid = models.CharField(max_length=64, unique=True)
    entity = models.CharField(max_length=30, db_index=True)
    entity_uuid = models.CharField(max_length=64, db_index=True)
    op = models.CharField(max_length=10)
    payload = models.JSONField(default=dict)
    device_id = models.CharField(max_length=64, db_index=True)
    user_name = models.CharField(max_length=100, blank=True, verbose_name='المستخدم')
    created_at = models.CharField(max_length=40)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('seq',)
        verbose_name = 'حدث مزامنة'
        verbose_name_plural = 'أحداث المزامنة'

    def __str__(self):
        return f'{self.seq} · {self.entity}.{self.op}'


class StockMove(models.Model):
    """حركة مخزون واحدة. الكمية المعروضة = مجموع الحركات، لا رقماً يُكتب فوقه.
    هكذا لا تضيع بيعة عند بيع حاسبتين بلا إنترنت في وقت واحد."""
    REASONS = [
        ('opening', 'رصيد افتتاحي'),
        ('sale', 'بيع في المحل'),
        ('sale_void', 'إلغاء وصل'),
        ('return', 'إرجاع من زبون'),
        ('adjust', 'تسوية يدوية'),
        ('online_order', 'طلب من الموقع'),
        ('online_order_cancel', 'إلغاء طلب من الموقع'),
    ]
    uuid = models.CharField(max_length=64, unique=True)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='stock_moves')
    product_uuid = models.CharField(max_length=64, db_index=True)
    delta = models.IntegerField(verbose_name='التغيير')
    reason = models.CharField(max_length=30, choices=REASONS, default='adjust')
    ref_type = models.CharField(max_length=20, blank=True)
    ref_uuid = models.CharField(max_length=64, blank=True, db_index=True)
    note = models.CharField(max_length=250, blank=True)
    device_id = models.CharField(max_length=64, blank=True)
    created_at = models.CharField(max_length=40)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-received_at',)
        verbose_name = 'حركة مخزون'
        verbose_name_plural = 'حركات المخزون'

    def __str__(self):
        return f'{self.product_uuid} {self.delta:+d} ({self.reason})'


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
