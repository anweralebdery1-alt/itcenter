import json
import secrets

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Value
from django.db.models.functions import LPad
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from .models import (
    MAX_PRODUCT_IMAGES,
    AppRelease,
    Category,
    Course,
    Customer,
    DownloadableFile,
    EducationalVideo,
    Order,
    OrderItem,
    PhoneOTP,
    PosDevice,
    PosEvent,
    Product,
    ProductImage,
    PushSubscription,
    StockMove,
    Review,
    SaleReservation,
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


class CategoryAdminForm(forms.ModelForm):
    """استمارة التصنيف: الأب يُختار بنفس القوائم المتتابعة المستعملة في المنتج."""

    class Meta:
        model = Category
        fields = ('name', 'parent', 'order', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'] = CategoryCascadeField(
            label='التصنيف الأب',
            help_text='اتركه فارغاً ليكون تصنيفاً رئيسياً.',
            exclude_branch=self.instance if self.instance.pk else None,
        )
        self.fields['parent'].initial = self.instance.parent_id


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """صفحة التصنيفات: شجرة واحدة للكل، وإضافة الفروع من مكانها.

    كانت قائمة مسطّحة من ٦٥ سطراً لا يُعرف منها من ابن من. صارت شجرة
    الرئيسية أولاً وتحت كل واحد فروعه، ومع كل عقدة زر «＋ فرع» يضيف تحتها
    مباشرة — نفس نقطة الإضافة التي تستعملها استمارة المنتج.
    """

    form = CategoryAdminForm
    list_display = ('name', 'parent', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)
    ordering = ('order', 'name')

    def get_urls(self):
        return [
            path('quick-add/', self.admin_site.admin_view(self.category_quick_add),
                 name='store_category_quick_add'),
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        # ?flat=1 يُرجع جدول جانغو المعتاد (للتعديل الجماعي والحذف)
        if request.GET.get('flat'):
            return super().changelist_view(request, extra_context)

        counts = dict(
            Product.objects.visible()
            .exclude(category__isnull=True)
            .values_list('category')
            .annotate(total=Count('id'))
        )
        nodes = list(Category.objects.order_by('order', 'name'))
        by_parent = {}
        for node in nodes:
            by_parent.setdefault(node.parent_id, []).append(node)

        def build(parent_id, depth):
            branch = []
            for node in by_parent.get(parent_id, []):
                subs = build(node.pk, depth + 1)
                branch.append({
                    'id': node.pk,
                    'name': node.name,
                    'is_active': node.is_active,
                    'own_count': counts.get(node.pk, 0),
                    'total_count': counts.get(node.pk, 0) + sum(s['total_count'] for s in subs),
                    'change_url': reverse('admin:store_category_change', args=[node.pk]),
                    'shop_url': f'/?view=electronics&category={node.pk}',
                    'subs': subs,
                })
            return branch

        context = {
            **self.admin_site.each_context(request),
            'title': 'التصنيفات',
            'opts': self.model._meta,
            'roots': build(None, 0),
            'total': len(nodes),
            'add_url': reverse('admin:store_category_quick_add'),
            'flat_url': f'{request.path}?flat=1',
            'can_add': request.user.has_perm('store.add_category'),
        }
        return TemplateResponse(request, 'admin/store/category_tree.html', context)

    def category_quick_add(self, request):
        """يضيف تصنيفاً من شجرة التصنيفات أو من استمارة المنتج بلا مغادرة الصفحة."""
        if request.method != 'POST':
            return JsonResponse({'ok': False, 'error': 'POST only'}, status=405)
        if not request.user.has_perm('store.add_category'):
            return JsonResponse({'ok': False, 'error': 'لا صلاحية لإضافة تصنيف.'},
                                status=403)

        name = (request.POST.get('name') or '').strip()
        if not name:
            return JsonResponse({'ok': False, 'error': 'اكتب اسم التصنيف.'})

        parent = None
        parent_id = (request.POST.get('parent') or '').strip()
        if parent_id:
            parent = Category.objects.filter(pk=parent_id).first()
            if parent is None:
                return JsonResponse({'ok': False, 'error': 'التصنيف الأب غير موجود.'})

        if Category.objects.filter(name=name, parent=parent).exists():
            return JsonResponse({'ok': False, 'error': f'«{name}» موجود هنا مسبقاً.'})

        category = Category.objects.create(name=name, parent=parent)
        return JsonResponse({
            'ok': True,
            'id': category.pk,
            'name': category.name,
            'parent': str(parent.pk) if parent else None,
        })


@admin.register(SiteSection)
class SiteSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'section_type', 'url', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('section_type', 'is_active')
    search_fields = ('title', 'description')


class ProductImagesWidget(forms.ClearableFileInput):
    """منطقة واحدة لكل صور المنتج: لصق (Ctrl+V) أو سحب أو اختيار من الحاسبة.

    استبدلت حقل «الصورة الرئيسية» أعلى الاستمارة وجدول «الصور الإضافية»
    أسفلها — كانا مكانين منفصلين لشيء واحد.
    """
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.product = None

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        value = files.get(name)
        return [value] if value else []

    def render(self, name, value, attrs=None, renderer=None):
        existing = []
        product = self.product
        if product is not None and product.pk:
            if product.image:
                existing.append({'token': 'main', 'url': product.image.url,
                                 'is_main': True})
            for extra in product.gallery_images.all():
                existing.append({'token': f'g{extra.pk}', 'url': extra.image.url,
                                 'is_main': False})
        return render_to_string('admin/store/product_images_widget.html', {
            'field_name': name,
            'existing': existing,
            'max_images': MAX_PRODUCT_IMAGES,
        })


class CategoryCascadeWidget(forms.Widget):
    """قوائم متتابعة للتصنيفات: الرئيسية أولاً، ثم أبناء ما اخترته، وهكذا.

    القائمة الطويلة الواحدة التي تسرد ٦٥ تصنيفاً بصيغة «الأب › الابن» صعبة
    التصفّح. هنا لا يرى المستخدم إلا ما يخصّ مستواه، ويستطيع إضافة تصنيف
    جديد في أي مستوى بلا مغادرة الصفحة.
    """

    def __init__(self, attrs=None, exclude_branch=None):
        super().__init__(attrs)
        # عند تعديل تصنيف لا يجوز أن يُعرض هو ولا فروعه كأب له
        self.excluded = set(exclude_branch.descendant_ids()) if exclude_branch else set()

    def get_context(self, name, value, attrs):
        return {}

    def value_from_datadict(self, data, files, name):
        return data.get(name) or None

    def render(self, name, value, attrs=None, renderer=None):
        tree = {'__roots__': []}
        queryset = Category.objects.filter(is_active=True).order_by('order', 'name')
        if self.excluded:
            queryset = queryset.exclude(pk__in=self.excluded)
        for category in queryset:
            tree[str(category.pk)] = {
                'name': category.name,
                'parent': str(category.parent_id) if category.parent_id else None,
                'children': [],
            }
        for key, item in tree.items():
            if key == '__roots__':
                continue
            if item['parent'] and item['parent'] in tree:
                tree[item['parent']]['children'].append(key)
            elif not item['parent']:
                tree['__roots__'].append(key)

        return render_to_string('admin/store/category_cascade_widget.html', {
            'field_name': name,
            'value': value or '',
            'tree_json': json.dumps(tree, ensure_ascii=False),
            'add_url': reverse('admin:store_category_quick_add'),
            'selected_path': value or '',
        })


class CategoryCascadeField(forms.ModelChoiceField):

    def __init__(self, *args, exclude_branch=None, **kwargs):
        kwargs.setdefault('queryset', Category.objects.all())
        kwargs.setdefault('required', False)
        kwargs.setdefault('label', 'التصنيف')
        kwargs.setdefault('widget', CategoryCascadeWidget(exclude_branch=exclude_branch))
        super().__init__(*args, **kwargs)


class MultiImageField(forms.FileField):
    """حقل يقبل عدة ملفات دفعة واحدة.

    forms.FileField القياسي يتحقق من ملف واحد ويرفض القائمة، فنُمرّر كل ملف
    على التحقق وحده ونُرجع قائمة نظيفة.
    """

    widget = ProductImagesWidget

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [super(MultiImageField, self).clean(item, initial)
                for item in data if item]


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

    product_images = MultiImageField(
        required=False,
        label='صور المنتج',
        help_text=f'حتى {MAX_PRODUCT_IMAGES} صور. الأولى هي الرئيسية.',
    )

    category = CategoryCascadeField(
        help_text='اختر المستوى الرئيسي، فتظهر قائمة أبنائه، وهكذا حتى آخر مستوى.',
    )

    class Meta:
        model = Product
        exclude = ('specifications', 'views_count', 'image')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product_images'].widget.product = self.instance
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

    def clean_product_images(self):
        uploads = [f for f in (self.cleaned_data.get('product_images') or []) if f]
        for upload in uploads:
            content_type = getattr(upload, 'content_type', '') or ''
            if not content_type.startswith('image/'):
                raise ValidationError(f'«{upload.name}» ليس صورة.')
        return uploads

    def clean(self):
        cleaned = super().clean()
        uploads = cleaned.get('product_images') or []
        removed = self._removed_tokens()

        kept = 0
        if self.instance and self.instance.pk:
            if self.instance.image and 'main' not in removed:
                kept += 1
            kept += sum(1 for extra in self.instance.gallery_images.all()
                        if f'g{extra.pk}' not in removed)

        if kept + len(uploads) > MAX_PRODUCT_IMAGES:
            raise ValidationError(
                f'الحد الأقصى {MAX_PRODUCT_IMAGES} صور للمنتج — '
                f'عندك {kept} وتحاول إضافة {len(uploads)}.')
        return cleaned

    def _removed_tokens(self):
        if hasattr(self.data, 'getlist'):
            return set(self.data.getlist('pi_remove'))
        return set()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.specifications = self.cleaned_data['specifications_text']
        if commit:
            instance.save()
            self.save_m2m()
            self.apply_images(instance)
        return instance

    def apply_images(self, product):
        """يُستدعى بعد حفظ المنتج.

        لوحة إدارة Django تستدعي save(commit=False) ثم تحفظ الكائن بنفسها،
        فلا يمكن وضع معالجة الصور داخل فرع commit=True — لن يُنفَّذ أبداً.
        """
        removed = self._removed_tokens()

        if 'main' in removed and product.image:
            product.image = None
            product.thumbnail = None
            product.save(update_fields=['image', 'thumbnail'])

        for extra in list(product.gallery_images.all()):
            if f'g{extra.pk}' in removed:
                extra.delete()

        self._store_uploads(product, self.cleaned_data.get('product_images') or [])

    def _store_uploads(self, product, uploads):
        """أول صورة تملأ الرئيسية إن كانت فارغة، والباقي في المعرض."""
        if not uploads:
            return
        pending = list(uploads)

        if not product.image:
            product.image = pending.pop(0)
            product.thumbnail = None
            product.save()

        used = set(product.gallery_images.values_list('position', flat=True))
        for upload in pending:
            position = next((slot for slot in range(1, MAX_PRODUCT_IMAGES)
                             if slot not in used), None)
            if position is None:
                break
            used.add(position)
            ProductImage.objects.create(product=product, image=upload, position=position)


class HasImageFilter(admin.SimpleListFilter):
    title = 'الصورة'
    parameter_name = 'has_image'

    def lookups(self, request, model_admin):
        return (('no', 'بلا صورة'), ('yes', 'لها صورة'))

    def queryset(self, request, queryset):
        if self.value() == 'no':
            return queryset.filter(Q(image='') | Q(image__isnull=True))
        if self.value() == 'yes':
            return queryset.exclude(Q(image='') | Q(image__isnull=True))
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    # قالب مخصّص: يُخفي الفلتر الجانبي ويضيف شريط دليل الألوان في الأعلى
    change_list_template = 'admin/store/product/change_list.html'

    def get_queryset(self, request):
        # نضيف تعليق sku_pad أولاً ثم نرتّب — وإلا رتّب الأساس قبل وجود التعليق.
        qs = self.model._default_manager.get_queryset().annotate(
            sku_pad=LPad('sku', 12, Value('0')))
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    @admin.display(description='SKU', ordering='sku_pad')
    def sku_col(self, obj):
        return obj.sku

    @admin.display(description='صورة')
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:46px;width:46px;object-fit:cover;'
                'border-radius:4px;border:1px solid #ddd" />', obj.image.url)
        return format_html('<span style="color:#c62828;font-size:11px">بلا صورة</span>')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        form.apply_images(obj)

    list_display = ('image_preview', 'name', 'sku_col', 'buy_price', 'sell_price', 'competitor_price',
                    'price_flag', 'review_flag', 'quantity', 'category',
                    'is_featured', 'is_offer', 'updated_at')
    list_editable = ('sell_price', 'competitor_price', 'quantity', 'is_featured', 'is_offer')
    search_fields = ('name', 'sku', 'description')
    # الفلاتر تبقى مسجّلة (لتعمل روابط القوائم السريعة في الشريط العلوي)،
    # لكن القالب المخصّص يُخفي شريطها الجانبي لتوسيع مساحة الجدول.
    list_filter = ('auto_filled', 'needs_review', HasImageFilter, 'is_featured', 'category', 'is_offer')

    def get_ordering(self, request):
        # الترتيب الافتراضي حسب SKU رقمياً (يعتمد تعليق sku_pad في get_queryset)
        return ['sku_pad']
    readonly_fields = ('uuid', 'views_count', 'created_at', 'updated_at')
    actions = ('mark_featured', 'unmark_featured', 'clear_review_flags')
    fieldsets = (
        ('صور المنتج', {
            'fields': ('product_images',),
            'description': 'الصق صورة منسوخة، أو اسحبها، أو اخترها من الحاسبة. '
                           'تُضاف مباشرة ويبقى المكان جاهزاً للصورة التالية.',
        }),
        ('بيانات المنتج', {
            'fields': ('name', 'sku', 'description', 'specifications_text'),
        }),
        ('الأسعار والمخزون', {
            'fields': ('buy_price', 'sell_price', 'competitor_price', 'quantity', 'is_offer'),
            'description': 'سعر المنافس = معدّل أوروك/أردنك. لوحة القائمة تلوّن الفرق بينه وبين سعر بيعك.',
        }),
        ('المراجعة والملء التلقائي', {
            'fields': ('auto_filled', 'needs_review', 'review_note'),
            'description': 'المنتجات المملوءة تلقائياً مُعلَّمة هنا. من قائمة المنتجات صفِّ بـ«مملوء تلقائياً» '
                           'أو «يحتاج انتباهاً» لمراجعة الدفعة، وبعد التأكد أزِل العلامتين.',
        }),
        ('الإبراز وأولوية الظهور', {
            'fields': ('is_featured', 'featured_priority'),
            'description': 'فعّل «منتج مميّز» ليظهر أولاً في الصفحة الرئيسية. الأولوية الأعلى تظهر قبل غيرها.',
        }),
        ('التنظيم', {'fields': ('category',)}),
        ('معلومات النظام', {'fields': ('uuid', 'views_count', 'created_at', 'updated_at')}),
    )

    @staticmethod
    def _badge(bg, text, fg='#fff'):
        return format_html(
            '<span style="background:{};color:{};padding:2px 6px;border-radius:4px;'
            'white-space:nowrap;font-size:11px">{}</span>', bg, fg, text)

    @admin.display(description='مقارنة السعر')
    def price_flag(self, obj):
        cp = obj.competitor_price or 0
        sp = obj.sell_price or 0
        if cp <= 0:
            return format_html('<span style="color:#999">—</span>')
        if sp <= 0:
            return format_html('<span style="color:#999">بلا سعر بيع</span>')
        diff = (sp - cp) / cp
        pct = round(diff * 100)
        if diff >= 0.30:
            return self._badge('#b71c1c', f'أعلى بكثير +{pct}%')
        if diff <= -0.30:
            return self._badge('#0d47a1', f'أقل بكثير {pct}%')
        if diff >= 0.10:
            return self._badge('#ef6c00', f'أعلى +{pct}%')
        if diff <= -0.10:
            return self._badge('#00838f', f'أقل {pct}%')
        return self._badge('#2e7d32', f'ضمن النطاق {pct:+d}%')

    @admin.display(description='مراجعة')
    def review_flag(self, obj):
        if obj.needs_review:
            return self._badge('#ff5252', 'راجعني')
        if obj.auto_filled:
            return self._badge('#ffca28', 'تلقائي', fg='#000')
        return ''

    @admin.action(description='إزالة علامة المراجعة/الملء التلقائي عن المحدد')
    def clear_review_flags(self, request, queryset):
        updated = queryset.update(auto_filled=False, needs_review=False)
        self.message_user(request, f'تم اعتماد {updated} منتجاً وإزالة علاماتها.')

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


@admin.register(AppRelease)
class AppReleaseAdmin(admin.ModelAdmin):
    list_display = ('version', 'is_active', 'is_mandatory', 'size_mb', 'created_at')
    list_editable = ('is_active', 'is_mandatory')
    readonly_fields = ('sha256', 'size_bytes', 'created_at')
    fields = ('version', 'installer', 'notes', 'is_active', 'is_mandatory',
              'sha256', 'size_bytes', 'created_at')

    @admin.display(description='الحجم')
    def size_mb(self, obj):
        return f'{(obj.size_bytes or 0) / 1048576:.1f} MB'


class PosDeviceAdminForm(forms.ModelForm):
    """معرّف الجهاز اختياري في اللوحة — يُولَّد تلقائياً إن تُرك فارغاً."""
    class Meta:
        model = PosDevice
        fields = ('name', 'device_id', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['device_id'].required = False
        self.fields['device_id'].help_text = (
            'اتركه فارغاً ليُولَّد تلقائياً. يميّز هذه الحاسبة عن غيرها في المزامنة.')


@admin.register(PosDevice)
class PosDeviceAdmin(admin.ModelAdmin):
    form = PosDeviceAdminForm
    list_display = ('name', 'device_id', 'is_active', 'last_seen', 'created_at')
    list_editable = ('is_active',)
    readonly_fields = ('token', 'last_seen', 'created_at')
    search_fields = ('name', 'device_id')

    def save_model(self, request, obj, form, change):
        """يولّد رمز اتصال ومعرّف جهاز فريدين عند الإنشاء، ثم يعرض الرمز لينسخه المالك.
        الرمز حقل للقراءة فقط في اللوحة، فلا يُدخَل يدوياً ولا يُنشأ جهاز بلا رمز."""
        creating = not change
        if creating:
            if not obj.device_id:
                obj.device_id = secrets.token_hex(16)
            if not obj.token:
                obj.token = secrets.token_hex(32)
        super().save_model(request, obj, form, change)
        if creating:
            self.message_user(request, format_html(
                'تم إنشاء الجهاز «{}». انسخ <b>رمز الاتصال</b> التالي وضعه في حقل '
                '«رمز الاتصال (٦٤ حرفاً)» بشاشة إعدادات هذه الحاسبة، ثم اضغط «مزامنة الآن»:'
                '<br><code style="user-select:all;font-size:14px;background:#f5f5f5;'
                'padding:4px 8px;display:inline-block;margin-top:6px;direction:ltr">{}</code>',
                obj.name or obj.device_id, obj.token))


@admin.register(StockMove)
class StockMoveAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'product_uuid', 'delta', 'reason', 'device_id', 'note')
    list_filter = ('reason', 'device_id')
    search_fields = ('product_uuid', 'ref_uuid', 'note')
    readonly_fields = tuple(field.name for field in StockMove._meta.fields)

    def has_add_permission(self, request):
        return False


@admin.register(PosEvent)
class PosEventAdmin(admin.ModelAdmin):
    list_display = ('seq', 'entity', 'op', 'user_name', 'entity_uuid', 'device_id',
                    'created_at', 'received_at')
    list_filter = ('entity', 'op', 'device_id', 'user_name')
    search_fields = ('uuid', 'entity_uuid')
    readonly_fields = tuple(field.name for field in PosEvent._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SaleReservation)
class SaleReservationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'total', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone', 'uuid')
    readonly_fields = ('uuid', 'created_at')
