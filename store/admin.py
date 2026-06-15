from django.contrib import admin
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
    SaleReservation,
    Series,
    SiteSection,
    SiteSettings,
    TeamMember,
)

admin.site.site_header = 'إدارة المتجر'
admin.site.site_title = 'إدارة المتجر'
admin.site.index_title = 'لوحة التحكم'


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('هوية الموقع', {'fields': ('site_name', 'tagline', 'logo')}),
        ('واجهة الصفحة الرئيسية', {'fields': ('hero_title', 'hero_subtitle', 'hero_image')}),
        ('ألوان المتجر', {'fields': ('primary_color', 'accent_color')}),
        ('معلومات التواصل', {'fields': ('phone', 'whatsapp', 'address')}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name',)
    list_filter = ('parent',)


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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'sell_price', 'quantity', 'category', 'is_offer', 'updated_at')
    list_editable = ('sell_price', 'quantity', 'is_offer')
    search_fields = ('name', 'sku', 'description')
    list_filter = ('category', 'series', 'is_offer')
    readonly_fields = ('uuid', 'created_at', 'updated_at')
    fieldsets = (
        ('بيانات المنتج', {'fields': ('name', 'sku', 'image', 'description', 'specifications')}),
        ('الأسعار والمخزون', {'fields': ('buy_price', 'sell_price', 'quantity', 'is_offer')}),
        ('التنظيم', {'fields': ('category', 'series')}),
        ('معلومات النظام', {'fields': ('uuid', 'created_at', 'updated_at')}),
    )


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
    list_display = ('title', 'video_url', 'is_active', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('title', 'description')
    inlines = (DownloadableFileInline,)


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
