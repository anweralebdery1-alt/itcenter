from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from .models import (
    Category,
    Course,
    Customer,
    DownloadableFile,
    EducationalVideo,
    Order,
    OrderItem,
    PhoneOTP,
    Product,
    ProductImage,
    PushSubscription,
    Review,
    SaleReservation,
    Series,
    SiteSection,
    SiteSettings,
    TeamMember,
)

admin.site.site_header = 'إدارة المتجر'
admin.site.site_title = 'إدارة المتجر'
admin.site.index_title = 'لوحة التحكم'


def _admin_badge(count):
    if not count:
        return ''
    return format_html(
        ' <span style="display:inline-grid;place-items:center;min-width:20px;height:20px;'
        'padding:0 6px;border-radius:999px;background:#d32f2f;color:#fff;'
        'font-size:12px;font-weight:700;line-height:1">{}</span>',
        count,
    )


def _badge_count_for_model(object_name):
    if object_name == 'Order':
        return Order.objects.filter(status='pending').count()
    if object_name == 'SaleReservation':
        return SaleReservation.objects.filter(status='reserved').count()
    if object_name == 'PhoneOTP':
        return PhoneOTP.objects.filter(is_used=False).count()
    return 0


_default_get_app_list = admin.site.get_app_list


def _get_app_list_with_badges(request, app_label=None):
    app_list = _default_get_app_list(request, app_label)
    for app in app_list:
        for model in app.get('models', []):
            badge = _admin_badge(_badge_count_for_model(model.get('object_name')))
            if badge:
                model['name'] = format_html('{}{}', model['name'], badge)
    return app_list


admin.site.get_app_list = _get_app_list_with_badges


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('هوية الموقع', {'fields': ('site_name', 'tagline', 'logo')}),
        ('واجهة الصفحة الرئيسية', {'fields': ('hero_title', 'hero_subtitle', 'hero_image')}),
        ('ألوان المتجر', {'fields': ('primary_color', 'accent_color')}),
        ('معلومات التواصل', {'fields': ('phone', 'whatsapp', 'address')}),
        ('تحسين محركات البحث (SEO)', {
            'fields': ('meta_description', 'meta_keywords', 'google_site_verification'),
            'description': 'إعدادات تساعد على ظهور المتجر في نتائج بحث جوجل بسرعة.',
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active', 'parent')
    ordering = ('order', 'name')
    fields = ('name', 'parent', 'order', 'is_active')


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(SiteSection)
class SiteSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'section_type', 'url', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('section_type', 'is_active')
    search_fields = ('title', 'description')


class ProductAdminForm(forms.ModelForm):
    specifications_text = forms.CharField(
        required=False,
        label='المواصفات',
        help_text='اكتب كل مواصفة في سطر مستقل بالشكل: الخاصية: القيمة',
        widget=forms.Textarea(
            attrs={
                'rows': 8,
                'placeholder': (
                    'نوع المتحكم: Arduino Uno\n'
                    'جهد التشغيل: 5V\n'
                    'اللون: أزرق'
                ),
            }
        ),
    )

    class Meta:
        model = Product
        exclude = ('specifications', 'views_count')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            specifications = self.instance.specifications or {}
            if isinstance(specifications, dict):
                self.fields['specifications_text'].initial = '\n'.join(
                    f'{key}: {value}'
                    for key, value in specifications.items()
                )

    def clean_specifications_text(self):
        raw_text = self.cleaned_data.get('specifications_text', '')
        specifications = {}
        for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue

            separators = [
                position
                for position in (line.find(':'), line.find('='), line.find('：'))
                if position > 0
            ]
            if not separators:
                raise ValidationError(
                    f'السطر {line_number} غير صحيح. '
                    'اكتب المواصفة بالشكل: الخاصية: القيمة'
                )

            separator_position = min(separators)
            key = line[:separator_position].strip()
            value = line[separator_position + 1:].strip()
            if not key or not value:
                raise ValidationError(
                    f'السطر {line_number} يجب أن يحتوي خاصية وقيمة.'
                )
            specifications[key] = value
        return specifications

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.specifications = self.cleaned_data['specifications_text']
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 4
    max_num = 4
    fields = ('image', 'position', 'alt_text')
    verbose_name = 'صورة إضافية'
    verbose_name_plural = 'صور إضافية اختيارية (أربع كحد أقصى)'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'sku', 'sell_price', 'quantity', 'category',
                    'is_featured', 'featured_priority', 'is_offer', 'views_count', 'updated_at')
    list_editable = ('sell_price', 'quantity', 'is_featured', 'featured_priority', 'is_offer')
    search_fields = ('name', 'sku', 'description')
    list_filter = ('is_featured', 'category', 'series', 'is_offer')
    ordering = ('-is_featured', 'featured_priority', '-updated_at')
    readonly_fields = ('uuid', 'views_count', 'created_at', 'updated_at')
    inlines = (ProductImageInline,)
    actions = ('mark_featured', 'unmark_featured')
    fieldsets = (
        ('بيانات المنتج', {
            'fields': ('name', 'sku', 'image', 'description', 'specifications_text'),
            'description': 'الصورة هنا هي الصورة الرئيسية. يمكن إضافة أربع صور اختيارية أخرى أسفل الصفحة.',
        }),
        ('الأسعار والمخزون', {'fields': ('buy_price', 'sell_price', 'quantity', 'is_offer')}),
        ('الإبراز وأولوية الظهور', {
            'fields': ('is_featured', 'featured_priority'),
            'description': 'فعّل «منتج مميّز» ليظهر أولاً في الصفحة الرئيسية. الأولوية الأعلى تظهر قبل غيرها.',
        }),
        ('التنظيم', {'fields': ('category', 'series')}),
        ('معلومات النظام', {'fields': ('uuid', 'views_count', 'created_at', 'updated_at')}),
    )

    @admin.action(description='تمييز المنتجات المحددة (إبراز)')
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'تم تمييز {updated} منتجاً.')

    @admin.action(description='إلغاء تمييز المنتجات المحددة')
    def unmark_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'تم إلغاء تمييز {updated} منتجاً.')


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('label', 'created_at')
    readonly_fields = ('endpoint', 'p256dh', 'auth', 'created_at')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'rating', 'is_approved', 'created_at')
    list_editable = ('is_approved',)
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('product__name', 'name', 'comment')
    readonly_fields = ('created_at',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'province', 'created_at')
    search_fields = ('full_name', 'phone', 'province')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_sku', 'product_name', 'price', 'quantity', 'line_total')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'province', 'payment_method', 'status', 'total', 'created_at')
    list_filter = ('payment_method', 'status', 'province', 'created_at')
    search_fields = ('full_name', 'phone', 'uuid')
    readonly_fields = ('uuid', 'created_at')
    inlines = (OrderItemInline,)


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ('phone', 'code', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('phone',)


class DownloadableFileInline(admin.TabularInline):
    model = DownloadableFile
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'trainer', 'price', 'duration', 'is_active', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('title', 'description', 'trainer')
    inlines = (DownloadableFileInline,)


@admin.register(EducationalVideo)
class EducationalVideoAdmin(admin.ModelAdmin):
    list_display = ('project_number', 'title', 'video_url', 'is_active', 'created_at')
    list_display_links = ('title',)
    list_editable = ('is_active',)
    ordering = ('project_number', 'id')
    search_fields = ('title', 'description', 'components')
    inlines = (DownloadableFileInline,)
    fields = ('title', 'video_url', 'thumbnail', 'description', 'components', 'wiring', 'code', 'source', 'is_active')
    actions = ('renumber_projects',)

    @admin.action(description='إعادة ترقيم المشاريع بالتسلسل (بلا فراغات)')
    def renumber_projects(self, request, queryset):
        import re
        n = 0
        for n, video in enumerate(EducationalVideo.objects.order_by('project_number', 'id'), start=1):
            title = re.sub(r'^مشروع\s*\d+\s*[:：]\s*', '', video.title).strip()
            video.project_number = n
            video.title = f'مشروع {n}: {title}'
            video.save(update_fields=['project_number', 'title'])
        self.message_user(request, f'تمت إعادة ترقيم {n} مشروعاً بالتسلسل.')


@admin.register(DownloadableFile)
class DownloadableFileAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_free', 'created_at')
    search_fields = ('title', 'description')


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'phone', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('name', 'role', 'bio', 'phone')


@admin.register(SaleReservation)
class SaleReservationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'total', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone', 'uuid')
    readonly_fields = ('uuid', 'created_at')
