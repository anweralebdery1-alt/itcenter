from django.db import migrations


# تصنيفات وظيفية (نوع المنتج) — تظهر في شريط التصنيفات للتصفية
CATEGORIES = [
    "لوحات التطوير والمتحكّمات",
    "الحسّاسات",
    "الموديولات",
    "الشاشات والعرض",
    "المحرّكات والتحكّم",
    "المكوّنات الإلكترونية",
    "الأسلاك والتوصيل",
    "الطاقة والبطاريات",
    "الطباعة ثلاثية الأبعاد",
    "الروبوت والأطقم التعليمية",
    "إنترنت الأشياء (IoT)",
    "العُدد والأدوات",
]

# السلاسل بحسب عائلات اللوحات/الأنظمة — تُستخدم للمنتجات المشابهة
SERIES = [
    "أردوينو (Arduino)",
    "راسبيري باي (Raspberry Pi)",
    "ESP32 / ESP8266",
    "STM32",
    "Micro:bit",
    "Orange Pi",
    "أطقم تعليمية (Kits)",
    "طائرات ودرون",
]


def seed(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    Series = apps.get_model("store", "Series")
    for name in CATEGORIES:
        Category.objects.get_or_create(name=name, parent=None)
    for name in SERIES:
        Series.objects.get_or_create(name=name)


def unseed(apps, schema_editor):
    # لا نحذف عند التراجع حتى لا نفقد ربط المنتجات بالتصنيفات
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0006_product_image_gallery"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
