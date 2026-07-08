# -*- coding: utf-8 -*-
import re
from django.db import migrations


AR = "شرح عربي"

GROUP3 = [
    {
        "title": "مقدمة: ما هو الأردوينو؟",
        "video_url": "https://www.youtube.com/watch?v=IGC0GsoQToE",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nدرس تمهيدي يعرّفك بلوحة الأردوينو ومكوّناتها وأطرافها وأين تُستخدم — نقطة البداية لكل مشروع.\n\n"
            "📘 تتعلّم:\n• ما هي لوحة الأردوينو وأنواعها.\n• الأطراف الرقمية والتماثلية والتغذية.\n• كيف تُرفع البرامج إليها."
        ),
        "components": "لوحة أردوينو أونو\nكابل USB\nحاسوب",
        "wiring": "",
        "code": "",
    },
    {
        "title": "تنصيب برنامج Arduino IDE",
        "video_url": "https://www.youtube.com/watch?v=kTqz5GNRKH4",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nتنزيل وتنصيب برنامج Arduino IDE وضبط إعداداته لرفع أول برنامج.\n\n"
            "📘 تتعلّم:\n• تنزيل البرنامج وتثبيته.\n• اختيار نوع اللوحة والمنفذ (Port).\n• رفع أول كود تجريبي."
        ),
        "components": "لوحة أردوينو أونو\nكابل USB\nحاسوب",
        "wiring": "",
        "code": "",
    },
    {
        "title": "شاشة LCD 16×2 (توصيل مباشر)",
        "video_url": "https://www.youtube.com/watch?v=FtV9pMCwvik",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nعرض النصوص على شاشة LCD بالتوصيل المباشر (بدون I2C) لفهم أطراف الشاشة.\n\n"
            "📘 الشرح:\n• الشاشة تُوصَّل بستّة أطراف بيانات + التباين + الإضاءة.\n• مكتبة LiquidCrystal للكتابة."
        ),
        "components": "أردوينو أونو\nشاشة LCD 16×2\nمقاومة متغيّرة 10 كيلو (للتباين)\nمقاومة 220 أوم (للإضاءة)\nأسلاك",
        "wiring": "RS←12 ، E←11\nD4←5 ، D5←4 ، D6←3 ، D7←2\nVSS←GND ، VDD←5V\nV0←الطرف الأوسط للمقاومة المتغيّرة\nA←5V عبر 220 ، K←GND",
        "code": (
            "#include <LiquidCrystal.h>\n"
            "LiquidCrystal lcd(12, 11, 5, 4, 3, 2);\n\n"
            "void setup() {\n"
            "  lcd.begin(16, 2);\n"
            "  lcd.print(\"IT Center\");\n"
            "  lcd.setCursor(0, 1);\n"
            "  lcd.print(\"Hello Arduino\");\n"
            "}\n\n"
            "void loop() {}\n"
        ),
    },
    {
        "title": "شاشة LCD مع وحدة I2C (نسخة ٢)",
        "video_url": "https://www.youtube.com/watch?v=61-GL5PiS1c",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنفس فكرة شاشة LCD لكن عبر وحدة I2C بسلكين فقط للبيانات — شرح إضافي.\n\n"
            "📘 الشرح:\n• وحدة I2C تقلّل الأسلاك إلى SDA و SCL.\n• العنوان غالباً 0x27 (قد يكون 0x3F)."
        ),
        "components": "أردوينو أونو\nشاشة LCD 16×2 مع وحدة I2C\nأسلاك",
        "wiring": "SDA ← A4\nSCL ← A5\nVCC ← 5V\nGND ← GND",
        "code": (
            "#include <LiquidCrystal_I2C.h>\n"
            "LiquidCrystal_I2C lcd(0x27, 16, 2);\n\n"
            "void setup() {\n"
            "  lcd.init(); lcd.backlight();\n"
            "  lcd.print(\"IT Center\");\n"
            "}\n\n"
            "void loop() {}\n"
        ),
    },
    {
        "title": "حسّاس الغاز MQ-5/MQ-2 (نسخة ٢)",
        "video_url": "https://www.youtube.com/watch?v=voWYHxuQjqY",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nشرح إضافي لكشف تسرّب الغاز/الدخان وإطلاق إنذار.\n\n"
            "📘 الشرح:\n• الحسّاس يعطي قيمة تماثلية ترتفع مع تركيز الغاز.\n• عند تجاوز الحدّ نشغّل البازر.\n⚠️ يحتاج تسخيناً قبل القراءات الدقيقة."
        ),
        "components": "أردوينو أونو\nحسّاس غاز MQ-2 أو MQ-5\nبازر\nأسلاك",
        "wiring": "A0 ← A0\nVCC ← 5V\nGND ← GND\nBuzzer ← الطرف 8 و GND",
        "code": (
            "int gas = A0, buzzer = 8;\n\n"
            "void setup() { pinMode(buzzer, OUTPUT); Serial.begin(9600); }\n\n"
            "void loop() {\n"
            "  int value = analogRead(gas);\n"
            "  Serial.println(value);\n"
            "  if (value > 400) tone(buzzer, 1000);\n"
            "  else noTone(buzzer);\n"
            "  delay(300);\n"
            "}\n"
        ),
    },
    {
        "title": "نظام ريّ ذكي بالترانزستور (نسخة ٢)",
        "video_url": "https://www.youtube.com/watch?v=v_BEYAx8KdU",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nشرح إضافي لريّ النبات تلقائياً، مع استخدام ترانزستور لتشغيل المضخّة.\n\n"
            "📘 الشرح:\n• حسّاس رطوبة التربة يقرأ الجفاف.\n• الترانزستور/الريليه يشغّل المضخّة عند الحاجة."
        ),
        "components": "أردوينو أونو\nحسّاس رطوبة التربة\nترانزستور أو ريليه\nمضخّة ماء صغيرة\nأسلاك",
        "wiring": "حسّاس التربة: AO←A0 ، VCC←5V ، GND←GND\nقاعدة الترانزستور ← الطرف 7 عبر مقاومة\nالمضخّة على المجمّع/الريليه",
        "code": (
            "int soil = A0, pump = 7;\n\n"
            "void setup() { pinMode(pump, OUTPUT); Serial.begin(9600); }\n\n"
            "void loop() {\n"
            "  int moisture = analogRead(soil);\n"
            "  Serial.println(moisture);\n"
            "  if (moisture > 600) digitalWrite(pump, HIGH);  // جافة → ريّ\n"
            "  else digitalWrite(pump, LOW);\n"
            "  delay(1000);\n"
            "}\n"
        ),
    },
    {
        "title": "ساعة الوقت الحقيقي RTC (نسخة ٢)",
        "video_url": "https://www.youtube.com/watch?v=C_ruorfhLbc",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nشرح إضافي للتعامل مع الوقت الحقيقي في الأردوينو عبر وحدة RTC.\n\n"
            "📘 الشرح:\n• RTC يحفظ الوقت ببطارية احتياطية.\n• نقرأ الوقت بمكتبة RTClib ونطبعه."
        ),
        "components": "أردوينو أونو\nوحدة RTC (DS3231 أو DS1307)\nأسلاك",
        "wiring": "SDA ← A4\nSCL ← A5\nVCC ← 5V\nGND ← GND",
        "code": (
            "#include <Wire.h>\n"
            "#include <RTClib.h>\n"
            "RTC_DS3231 rtc;\n\n"
            "void setup() {\n"
            "  Serial.begin(9600); rtc.begin();\n"
            "  // rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));\n"
            "}\n\n"
            "void loop() {\n"
            "  DateTime now = rtc.now();\n"
            "  Serial.print(now.hour()); Serial.print(':');\n"
            "  Serial.print(now.minute()); Serial.print(':');\n"
            "  Serial.println(now.second());\n"
            "  delay(1000);\n"
            "}\n"
        ),
    },
    {
        "title": "🔐 باب ذكي RFID مع شاشة LCD",
        "video_url": "https://www.youtube.com/watch?v=JbdkE5pXoRs",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nباب يفتح بالبطاقة المصرّح بها ويعرض رسالة ترحيب/رفض على شاشة LCD — مشروع أمان متكامل.\n\n"
            "📘 الشرح:\n• RFID يقرأ UID البطاقة.\n• إن طابقت المصرّح: يفتح السيرفو ويكتب Welcome، وإلا Access Denied."
        ),
        "components": "أردوينو أونو\nوحدة RFID RC522 + بطاقات\nمحرّك سيرفو SG90\nشاشة LCD I2C\nأسلاك",
        "wiring": "RFID: SDA←10, SCK←13, MOSI←11, MISO←12, RST←9, 3.3V←3V3\nالسيرفو ← الطرف 3\nLCD I2C: SDA←A4 ، SCL←A5",
        "code": (
            "#include <SPI.h>\n"
            "#include <MFRC522.h>\n"
            "#include <Servo.h>\n"
            "#include <LiquidCrystal_I2C.h>\n"
            "#define SS_PIN 10\n"
            "#define RST_PIN 9\n"
            "MFRC522 rfid(SS_PIN, RST_PIN);\n"
            "Servo lock;\n"
            "LiquidCrystal_I2C lcd(0x27, 16, 2);\n"
            "String allowed = \"A1B2C3D4\";\n\n"
            "String readUID() {\n"
            "  String u = \"\";\n"
            "  for (byte i = 0; i < rfid.uid.size; i++) u += String(rfid.uid.uidByte[i], HEX);\n"
            "  u.toUpperCase(); return u;\n"
            "}\n\n"
            "void setup() {\n"
            "  SPI.begin(); rfid.PCD_Init(); lock.attach(3); lock.write(0);\n"
            "  lcd.init(); lcd.backlight(); lcd.print(\"Scan your card\");\n"
            "}\n\n"
            "void loop() {\n"
            "  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {\n"
            "    lcd.clear();\n"
            "    if (readUID() == allowed) { lcd.print(\"Welcome\"); lock.write(90); delay(3000); lock.write(0); }\n"
            "    else { lcd.print(\"Access Denied\"); }\n"
            "    delay(1500); lcd.clear(); lcd.print(\"Scan your card\");\n"
            "    rfid.PICC_HaltA();\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "title": "التحكّم بالبلوتوث HC-05 (نسخة ٢)",
        "video_url": "https://www.youtube.com/watch?v=CpEAww3dy-g",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nشرح إضافي لبرمجة وتشغيل وحدة البلوتوث والتحكّم من الهاتف.\n\n"
            "📘 الشرح:\n• HC-05 تستقبل أوامر من تطبيق بلوتوث.\n• نقرأ الحرف الوارد ونتحكّم بالمخرج."
        ),
        "components": "أردوينو أونو\nوحدة بلوتوث HC-05\nليد + مقاومة 220\nأسلاك",
        "wiring": "HC-05 TX ← الطرف 2 ، RX ← الطرف 3\nVCC ← 5V ، GND ← GND\nليد ← 220 ← الطرف 13",
        "code": (
            "#include <SoftwareSerial.h>\n"
            "SoftwareSerial BT(2, 3);\n"
            "int led = 13;\n\n"
            "void setup() { BT.begin(9600); pinMode(led, OUTPUT); }\n\n"
            "void loop() {\n"
            "  if (BT.available()) {\n"
            "    char c = BT.read();\n"
            "    if (c == '1') digitalWrite(led, HIGH);\n"
            "    if (c == '0') digitalWrite(led, LOW);\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "title": "🚗 سيارة روبوت بلوتوث (نسخة ٢ مع شرح الكود)",
        "video_url": "https://www.youtube.com/watch?v=BaGwb14svaI",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nشرح إضافي لقيادة سيارة روبوت من الهاتف عبر البلوتوث مع تفصيل الكود.\n\n"
            "📘 الشرح:\n• التطبيق يرسل حرفاً لكل اتجاه.\n• نتحكّم بالمحرّكات عبر L298N."
        ),
        "components": "أردوينو أونو\nهيكل سيارة ومحرّكَي DC\nدرايفر L298N\nوحدة بلوتوث HC-05\nبطارية وأسلاك",
        "wiring": "L298N: IN1←5, IN2←6, IN3←9, IN4←10\nHC-05: TX←2 ، RX←3\nتغذية وGND مشترك",
        "code": (
            "#include <SoftwareSerial.h>\n"
            "SoftwareSerial BT(2, 3);\n"
            "int IN1 = 5, IN2 = 6, IN3 = 9, IN4 = 10;\n\n"
            "void setM(int a, int b, int c, int d) {\n"
            "  digitalWrite(IN1,a); digitalWrite(IN2,b); digitalWrite(IN3,c); digitalWrite(IN4,d);\n"
            "}\n\n"
            "void setup() {\n"
            "  BT.begin(9600);\n"
            "  pinMode(IN1,OUTPUT); pinMode(IN2,OUTPUT); pinMode(IN3,OUTPUT); pinMode(IN4,OUTPUT);\n"
            "}\n\n"
            "void loop() {\n"
            "  if (BT.available()) {\n"
            "    char c = BT.read();\n"
            "    if (c == 'F') setM(1,0,1,0);\n"
            "    else if (c == 'B') setM(0,1,0,1);\n"
            "    else if (c == 'L') setM(0,1,1,0);\n"
            "    else if (c == 'R') setM(1,0,0,1);\n"
            "    else setM(0,0,0,0);\n"
            "  }\n"
            "}\n"
        ),
    },
]


def seed_and_number(apps, schema_editor):
    EducationalVideo = apps.get_model("store", "EducationalVideo")
    # 1) أضف مجموعة 3
    for item in GROUP3:
        EducationalVideo.objects.get_or_create(
            video_url=item["video_url"],
            defaults={k: v for k, v in item.items() if k != "video_url"},
        )
    # 2) رقّم كل المشاريع وأعِد تسمية العناوين إلى "مشروع N: ..."
    for n, video in enumerate(EducationalVideo.objects.order_by("id"), start=1):
        title = video.title
        title = re.sub(r"^مشروع\s*\d+\s*[:：]\s*", "", title)      # أزل ترقيماً سابقاً
        title = re.sub(r"^\s*[٠-٩\d]+\)\s*", "", title)  # أزل بادئة "N) "
        video.project_number = n
        video.title = "مشروع {}: {}".format(n, title.strip())
        video.save(update_fields=["project_number", "title"])


def reverse(apps, schema_editor):
    EducationalVideo = apps.get_model("store", "EducationalVideo")
    urls = [p["video_url"] for p in GROUP3]
    EducationalVideo.objects.filter(video_url__in=urls).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0023_alter_educationalvideo_options_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_and_number, reverse),
    ]
