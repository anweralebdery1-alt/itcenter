# -*- coding: utf-8 -*-
from django.db import migrations


AR = "شرح عربي"

PROJECTS = [
    {
        "title": "٢٠) قياس الحرارة والرطوبة DHT11",
        "video_url": "https://www.youtube.com/watch?v=aw9dZ0yUgRQ",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنقرأ درجة الحرارة والرطوبة من حسّاس DHT11 ونعرضها على الشاشة التسلسلية — أساس محطات الطقس والتحكّم بالمناخ.\n\n"
            "📘 الشرح:\n• DHT11 يعطي الحرارة والرطوبة رقمياً.\n• مكتبة DHT تقرأهما بدالتين readTemperature و readHumidity.\n• تحتاج تثبيت مكتبة DHT sensor library."
        ),
        "components": "أردوينو أونو\nحسّاس DHT11\nمقاومة 10 كيلو (اختيارية)\nأسلاك توصيل",
        "wiring": "VCC ← 5V\nGND ← GND\nDATA ← الطرف 2",
        "code": (
            "#include <DHT.h>\n"
            "#define DHTPIN 2\n"
            "#define DHTTYPE DHT11\n"
            "DHT dht(DHTPIN, DHTTYPE);\n\n"
            "void setup() {\n"
            "  Serial.begin(9600); dht.begin();\n"
            "}\n\n"
            "void loop() {\n"
            "  float h = dht.readHumidity();\n"
            "  float t = dht.readTemperature();\n"
            "  Serial.print(\"Temp: \"); Serial.print(t);\n"
            "  Serial.print(\"C  Hum: \"); Serial.print(h); Serial.println(\"%\");\n"
            "  delay(2000);\n"
            "}\n"
        ),
    },
    {
        "title": "٢١) 🌱 نظام ريّ تلقائي للنبات",
        "video_url": "https://www.youtube.com/watch?v=jcpSSiRMT44",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنسقي النبات تلقائياً عند جفاف التربة — يوفّر الوقت ويحافظ على النبات.\n\n"
            "📘 الشرح:\n• حسّاس رطوبة التربة يقرأ الجفاف (قيمة عالية = جافة).\n• عند تجاوز الحدّ نشغّل مضخّة ماء عبر ريليه.\n⚠️ عتبة القراءة تختلف حسب الحسّاس فاضبطها بالتجربة."
        ),
        "components": "أردوينو أونو\nحسّاس رطوبة التربة\nوحدة ريليه (Relay)\nمضخّة ماء صغيرة 5V\nأسلاك",
        "wiring": "حسّاس التربة: AO ← A0 ، VCC ← 5V ، GND ← GND\nالريليه IN ← الطرف 7\nالمضخّة تُوصَّل عبر الريليه",
        "code": (
            "int soil = A0, relay = 7;\n\n"
            "void setup() {\n"
            "  pinMode(relay, OUTPUT); Serial.begin(9600);\n"
            "}\n\n"
            "void loop() {\n"
            "  int moisture = analogRead(soil);\n"
            "  Serial.println(moisture);\n"
            "  if (moisture > 600) digitalWrite(relay, HIGH);  // تربة جافة → شغّل المضخّة\n"
            "  else digitalWrite(relay, LOW);\n"
            "  delay(1000);\n"
            "}\n"
        ),
    },
    {
        "title": "٢٢) حسّاس مستوى الماء",
        "video_url": "https://www.youtube.com/watch?v=i3WH_KsxTIs",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنكتشف مستوى الماء في خزّان ونشغّل تنبيهاً عند الامتلاء أو الانخفاض.\n\n"
            "📘 الشرح:\n• الحسّاس يعطي قيمة تماثلية تزيد مع ارتفاع الماء.\n• نقارنها بحدّ ونشغّل ليداً/إنذاراً."
        ),
        "components": "أردوينو أونو\nحسّاس مستوى الماء\nليد + مقاومة 220 أوم\nأسلاك",
        "wiring": "S ← A0\n+ ← 5V\n− ← GND\nليد ← 220 ← الطرف 13",
        "code": (
            "int water = A0, led = 13;\n\n"
            "void setup() {\n"
            "  pinMode(led, OUTPUT); Serial.begin(9600);\n"
            "}\n\n"
            "void loop() {\n"
            "  int level = analogRead(water);\n"
            "  Serial.println(level);\n"
            "  if (level > 300) digitalWrite(led, HIGH);  // ماء مرتفع → تنبيه\n"
            "  else digitalWrite(led, LOW);\n"
            "  delay(500);\n"
            "}\n"
        ),
    },
    {
        "title": "٢٣) 🔥 حسّاس الغاز MQ-2 (إنذار تسرّب)",
        "video_url": "https://www.youtube.com/watch?v=W4NZnqAabjs",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنكتشف تسرّب الغاز أو الدخان ونطلق إنذاراً — أساس أنظمة السلامة المنزلية.\n\n"
            "📘 الشرح:\n• MQ-2 يعطي قيمة تماثلية ترتفع مع تركيز الغاز.\n• عند تجاوز الحدّ نشغّل البازر.\n⚠️ يحتاج الحسّاس دقائق للتسخين قبل قراءات دقيقة."
        ),
        "components": "أردوينو أونو\nحسّاس غاز MQ-2\nبازر (Buzzer)\nأسلاك",
        "wiring": "A0 ← A0\nVCC ← 5V\nGND ← GND\nBuzzer ← الطرف 8 و GND",
        "code": (
            "int gas = A0, buzzer = 8;\n\n"
            "void setup() {\n"
            "  pinMode(buzzer, OUTPUT); Serial.begin(9600);\n"
            "}\n\n"
            "void loop() {\n"
            "  int value = analogRead(gas);\n"
            "  Serial.println(value);\n"
            "  if (value > 400) { tone(buzzer, 1000); }  // تسرّب → إنذار\n"
            "  else { noTone(buzzer); }\n"
            "  delay(300);\n"
            "}\n"
        ),
    },
    {
        "title": "٢٤) قارئ بطاقات RFID RC522",
        "video_url": "https://www.youtube.com/watch?v=96wFohRBv2k",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنقرأ رقم (UID) أي بطاقة RFID — أساس أنظمة الحضور والأقفال الذكية.\n\n"
            "📘 الشرح:\n• RC522 يقرأ البطاقات عبر SPI.\n• مكتبة MFRC522 تعطينا UID كلّ بطاقة.\n⚠️ يعمل الموديول على 3.3 فولت فقط."
        ),
        "components": "أردوينو أونو\nوحدة RFID RC522 + بطاقات\nأسلاك",
        "wiring": "SDA(SS) ← 10 ، SCK ← 13 ، MOSI ← 11\nMISO ← 12 ، RST ← 9 ، 3.3V ← 3V3 ، GND ← GND",
        "code": (
            "#include <SPI.h>\n"
            "#include <MFRC522.h>\n"
            "#define SS_PIN 10\n"
            "#define RST_PIN 9\n"
            "MFRC522 rfid(SS_PIN, RST_PIN);\n\n"
            "void setup() {\n"
            "  Serial.begin(9600); SPI.begin(); rfid.PCD_Init();\n"
            "}\n\n"
            "void loop() {\n"
            "  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {\n"
            "    Serial.print(\"UID: \");\n"
            "    for (byte i = 0; i < rfid.uid.size; i++) {\n"
            "      Serial.print(rfid.uid.uidByte[i], HEX); Serial.print(\" \");\n"
            "    }\n"
            "    Serial.println();\n"
            "    rfid.PICC_HaltA();\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "title": "٢٥) 🔐 قفل باب ذكي بالبطاقة RFID + سيرفو",
        "video_url": "https://www.youtube.com/watch?v=iDEppWMba5I",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nيفتح الباب فقط عند تمرير بطاقة مصرّح بها — مشروع أمان عملي.\n\n"
            "📘 الشرح:\n• نقرأ UID البطاقة.\n• إن طابق البطاقة المصرّح بها يحرّك السيرفو ليفتح 3 ثوانٍ.\n• ضع UID بطاقتك في المتغيّر allowed."
        ),
        "components": "أردوينو أونو\nوحدة RFID RC522 + بطاقات\nمحرّك سيرفو SG90\nأسلاك",
        "wiring": "RFID كما في المشروع السابق\nالسيرفو ← الطرف 3",
        "code": (
            "#include <SPI.h>\n"
            "#include <MFRC522.h>\n"
            "#include <Servo.h>\n"
            "#define SS_PIN 10\n"
            "#define RST_PIN 9\n"
            "MFRC522 rfid(SS_PIN, RST_PIN);\n"
            "Servo lock;\n"
            "String allowed = \"A1B2C3D4\";  // ضع UID بطاقتك هنا\n\n"
            "String readUID() {\n"
            "  String uid = \"\";\n"
            "  for (byte i = 0; i < rfid.uid.size; i++) uid += String(rfid.uid.uidByte[i], HEX);\n"
            "  uid.toUpperCase(); return uid;\n"
            "}\n\n"
            "void setup() {\n"
            "  Serial.begin(9600); SPI.begin(); rfid.PCD_Init();\n"
            "  lock.attach(3); lock.write(0);\n"
            "}\n\n"
            "void loop() {\n"
            "  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {\n"
            "    if (readUID() == allowed) { lock.write(90); delay(3000); lock.write(0); }\n"
            "    rfid.PICC_HaltA();\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "title": "٢٦) لوحة مفاتيح Keypad 4×4",
        "video_url": "https://www.youtube.com/watch?v=RWI2aoAO-FI",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنقرأ ضغطات لوحة مفاتيح 4×4 — أساس أنظمة إدخال كلمة السر والقوائم.\n\n"
            "📘 الشرح:\n• مكتبة Keypad تحوّل الصفوف والأعمدة إلى أحرف.\n• getKey() تعيد الزر المضغوط.\n• يمكن دمجها مع سيرفو لعمل قفل بكلمة سر."
        ),
        "components": "أردوينو أونو\nلوحة مفاتيح 4×4\nأسلاك",
        "wiring": "الصفوف ← الأطراف 2, 3, 4, 5\nالأعمدة ← الأطراف 6, 7, 8, 9",
        "code": (
            "#include <Keypad.h>\n"
            "const byte ROWS = 4, COLS = 4;\n"
            "char keys[ROWS][COLS] = {\n"
            "  {'1','2','3','A'},\n"
            "  {'4','5','6','B'},\n"
            "  {'7','8','9','C'},\n"
            "  {'*','0','#','D'}\n"
            "};\n"
            "byte rowPins[ROWS] = {2, 3, 4, 5};\n"
            "byte colPins[COLS] = {6, 7, 8, 9};\n"
            "Keypad kp = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);\n\n"
            "void setup() { Serial.begin(9600); }\n\n"
            "void loop() {\n"
            "  char k = kp.getKey();\n"
            "  if (k) Serial.println(k);\n"
            "}\n"
        ),
    },
    {
        "title": "٢٧) ⏰ ساعة رقمية RTC DS3231 + شاشة",
        "video_url": "https://www.youtube.com/watch?v=hO9PQhu6Ld4",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنبني ساعة تعرض الوقت والتاريخ وتحتفظ بهما حتى بعد فصل الكهرباء.\n\n"
            "📘 الشرح:\n• DS3231 ساعة دقيقة ببطارية احتياطية.\n• مكتبة RTClib تقرأ الوقت، ونعرضه على شاشة LCD I2C.\n• اضبط الوقت مرّة واحدة بسطر rtc.adjust ثم علّق عليه."
        ),
        "components": "أردوينو أونو\nوحدة ساعة RTC DS3231\nشاشة LCD 16×2 I2C\nأسلاك",
        "wiring": "RTC و LCD على ناقل I2C:\nSDA ← A4 ، SCL ← A5 ، VCC ← 5V ، GND ← GND",
        "code": (
            "#include <Wire.h>\n"
            "#include <RTClib.h>\n"
            "#include <LiquidCrystal_I2C.h>\n"
            "RTC_DS3231 rtc;\n"
            "LiquidCrystal_I2C lcd(0x27, 16, 2);\n\n"
            "void setup() {\n"
            "  lcd.init(); lcd.backlight(); rtc.begin();\n"
            "  // rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); // اضبط الوقت مرّة ثم علّق\n"
            "}\n\n"
            "void loop() {\n"
            "  DateTime now = rtc.now();\n"
            "  lcd.setCursor(0, 0);\n"
            "  lcd.print(now.hour()); lcd.print(\":\"); lcd.print(now.minute());\n"
            "  lcd.print(\":\"); lcd.print(now.second()); lcd.print(\"  \");\n"
            "  lcd.setCursor(0, 1);\n"
            "  lcd.print(now.day()); lcd.print(\"/\"); lcd.print(now.month());\n"
            "  lcd.print(\"/\"); lcd.print(now.year());\n"
            "  delay(1000);\n"
            "}\n"
        ),
    },
    {
        "title": "٢٨) التحكّم بزاوية السيرفو بمقياس جهد",
        "video_url": "https://www.youtube.com/watch?v=I6crtYLNYlg",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nندير محرّك السيرفو يدوياً بتدوير مقاومة متغيّرة (مقبض تحكّم).\n\n"
            "📘 الشرح:\n• analogRead يقرأ موضع المقاومة (0–1023).\n• map يحوّلها إلى زاوية (0–180).\n• write يوجّه السيرفو للزاوية مباشرة."
        ),
        "components": "أردوينو أونو\nمحرّك سيرفو SG90\nمقاومة متغيّرة 10 كيلو\nأسلاك",
        "wiring": "السيرفو (الإشارة) ← الطرف 9\nالمقاومة: الأوسط ← A0 ، الجانبان ← 5V و GND",
        "code": (
            "#include <Servo.h>\n"
            "Servo myServo;\n"
            "int pot = A0;\n\n"
            "void setup() { myServo.attach(9); }\n\n"
            "void loop() {\n"
            "  int v = analogRead(pot);\n"
            "  int angle = map(v, 0, 1023, 0, 180);\n"
            "  myServo.write(angle);\n"
            "  delay(15);\n"
            "}\n"
        ),
    },
    {
        "title": "٢٩) 🌈 شريط ليد ملوّن WS2812",
        "video_url": "https://www.youtube.com/watch?v=fRBJO0IZfxk",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنتحكّم بشريط ليد قابل للعنونة (كل ليد بلونه) لعمل تأثيرات ضوئية.\n\n"
            "📘 الشرح:\n• كل ليد في الشريط له عنوان مستقل.\n• مكتبة Adafruit_NeoPixel تضبط لون كل ليد.\n⚠️ للأشرطة الطويلة استخدم مصدر 5V منفصل و GND مشترك."
        ),
        "components": "أردوينو أونو\nشريط ليد WS2812 (NeoPixel)\nمقاومة 330 أوم\nمكثّف 1000µF (اختياري)\nمصدر طاقة 5V وأسلاك",
        "wiring": "DIN ← 330 ← الطرف 6\n+5V ← مصدر 5V\nGND ← GND مشترك",
        "code": (
            "#include <Adafruit_NeoPixel.h>\n"
            "#define PIN 6\n"
            "#define N 30\n"
            "Adafruit_NeoPixel strip(N, PIN, NEO_GRB + NEO_KHZ800);\n\n"
            "void setup() { strip.begin(); strip.show(); }\n\n"
            "void loop() {\n"
            "  for (int i = 0; i < N; i++) {\n"
            "    strip.setPixelColor(i, strip.Color(0, 0, 255));\n"
            "    strip.show(); delay(50);\n"
            "  }\n"
            "  for (int i = 0; i < N; i++) strip.setPixelColor(i, strip.Color(0, 0, 0));\n"
            "  strip.show(); delay(200);\n"
            "}\n"
        ),
    },
]


def seed(apps, schema_editor):
    EducationalVideo = apps.get_model("store", "EducationalVideo")
    for item in PROJECTS:
        EducationalVideo.objects.get_or_create(
            video_url=item["video_url"],
            defaults={k: v for k, v in item.items() if k != "video_url"},
        )


def unseed(apps, schema_editor):
    EducationalVideo = apps.get_model("store", "EducationalVideo")
    urls = [p["video_url"] for p in PROJECTS]
    EducationalVideo.objects.filter(video_url__in=urls).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0021_reseed_full_videos"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
