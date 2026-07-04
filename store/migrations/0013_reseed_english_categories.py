from django.db import migrations


# 12 تصنيفاً رئيسياً بالإنجليزية، وداخل كل واحد تصنيفاته الفرعية.
# الترتيب في القائمة = أولوية الظهور في شريط التصنيفات (يمكن تعديلها لاحقاً من الأدمن).
HIERARCHY = [
    ("Arduino", ["Arduino Boards", "Shields", "Arduino Kits", "Compatible Modules"]),
    ("Raspberry Pi", ["Pi Boards", "Pi Pico", "HATs & Add-ons", "Accessories"]),
    ("ESP & IoT", ["ESP32", "ESP8266", "WiFi & Bluetooth", "IoT Modules"]),
    ("Sensors", ["Temperature & Humidity", "Motion & Proximity", "Distance", "Light & Color", "Gas & Air"]),
    ("Motors & Drivers", ["DC Motors", "Servo Motors", "Stepper Motors", "Motor Drivers", "Pumps"]),
    ("Displays", ["OLED", "LCD", "TFT", "LED Matrix", "7-Segment"]),
    ("Components", ["Resistors", "Capacitors", "Diodes", "Transistors", "ICs"]),
    ("Power & Batteries", ["Adapters", "Batteries", "Chargers", "Solar", "Regulators"]),
    ("Prototyping & Wires", ["Breadboards", "Jumper Wires", "Connectors", "PCBs"]),
    ("Tools", ["Soldering", "Multimeters & Meters", "Hand Tools", "3D Printing"]),
    ("Robotics & Kits", ["Robot Cars", "STEM Kits", "Drones", "Chassis & Wheels"]),
    ("Modules & Communication", ["Relays", "RF & Bluetooth", "RFID", "Memory & Storage"]),
]


def reseed(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    # حذف التصنيفات المزروعة سابقاً (بالعربية) للبدء بهيكل إنجليزي نظيف.
    # المنتجات لا تُحذف (category = SET_NULL) لكنها قد تحتاج إعادة تصنيف يدوياً.
    Category.objects.all().delete()
    for main_order, (main_name, subs) in enumerate(HIERARCHY, start=1):
        parent = Category.objects.create(name=main_name, parent=None, order=main_order, is_active=True)
        for sub_order, sub_name in enumerate(subs, start=1):
            Category.objects.create(name=sub_name, parent=parent, order=sub_order, is_active=True)


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0012_alter_category_options_category_is_active_and_more"),
    ]

    operations = [
        migrations.RunPython(reseed, unseed),
    ]
