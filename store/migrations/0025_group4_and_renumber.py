# -*- coding: utf-8 -*-
import re
from django.db import migrations


AR = "شرح عربي"

GROUP4 = [
    {
        "title": "محرك السيرفو (نسخة ٢)",
        "video_url": "https://www.youtube.com/watch?v=dUegv3_boTo",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nشرح إضافي لمحرّك السيرفو وكيفية التحكّم بزاويته.\n\n"
            "📘 الشرح:\n• مكتبة Servo تتحكّم بالزاوية 0–180.\n• attach لتحديد الطرف، write لضبط الزاوية."
        ),
        "components": "أردوينو أونو\nمحرّك سيرفو SG90\nأسلاك",
        "wiring": "الإشارة ← الطرف 9\n+ ← 5V\n− ← GND",
        "code": (
            "#include <Servo.h>\n"
            "Servo myServo;\n\n"
            "void setup() { myServo.attach(9); }\n\n"
            "void loop() {\n"
            "  for (int p = 0; p <= 180; p++) { myServo.write(p); delay(15); }\n"
            "  for (int p = 180; p >= 0; p--) { myServo.write(p); delay(15); }\n"
            "}\n"
        ),
    },
    {
        "title": "المداخل والمخارج مع السيرفو",
        "video_url": "https://www.youtube.com/watch?v=x1UPzeSu5T4",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنجمع بين قراءة مدخل (زر) وتشغيل مخرج (سيرفو): الضغط يحرّك السيرفو.\n\n"
            "📘 الشرح:\n• digitalRead يقرأ الزر.\n• حسب حالته نضبط زاوية السيرفو."
        ),
        "components": "أردوينو أونو\nمحرّك سيرفو SG90\nزر ضاغط + مقاومة 10 كيلو\nأسلاك",
        "wiring": "الزر ← الطرف 2 (مع 10 كيلو إلى GND)\nالسيرفو ← الطرف 9",
        "code": (
            "#include <Servo.h>\n"
            "Servo s; int button = 2;\n\n"
            "void setup() { s.attach(9); pinMode(button, INPUT); s.write(0); }\n\n"
            "void loop() {\n"
            "  if (digitalRead(button) == HIGH) s.write(90);\n"
            "  else s.write(0);\n"
            "}\n"
        ),
    },
    {
        "title": "الليد ثلاثي الألوان RGB (نسخة ٢)",
        "video_url": "https://www.youtube.com/watch?v=7PBafnbZffQ",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nشرح إضافي لتوليد الألوان بمزج الأحمر والأخضر والأزرق عبر PWM.\n\n"
            "📘 الشرح:\n• analogWrite لكل لون (0–255).\n• مزج الشدّات يعطي ألواناً متعددة."
        ),
        "components": "أردوينو أونو\nليد RGB (كاثود مشترك)\n3 مقاومات 220 أوم\nأسلاك",
        "wiring": "الأحمر ← 220 ← 9\nالأخضر ← 220 ← 10\nالأزرق ← 220 ← 11\nالمشترك ← GND",
        "code": (
            "int R = 9, G = 10, B = 11;\n"
            "void setColor(int r, int g, int b) { analogWrite(R,r); analogWrite(G,g); analogWrite(B,b); }\n\n"
            "void setup() { pinMode(R,OUTPUT); pinMode(G,OUTPUT); pinMode(B,OUTPUT); }\n\n"
            "void loop() {\n"
            "  setColor(255,0,0); delay(600);\n"
            "  setColor(0,255,0); delay(600);\n"
            "  setColor(0,0,255); delay(600);\n"
            "}\n"
        ),
    },
    {
        "title": "شريط ليد WS2812 (نسخة ٢)",
        "video_url": "https://www.youtube.com/watch?v=o8R0bpQv22c",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nشرح إضافي للتحكّم بشريط ليد قابل للعنونة وعمل تأثيرات ضوئية.\n\n"
            "📘 الشرح:\n• كل ليد له عنوان مستقل.\n• مكتبة Adafruit_NeoPixel لضبط لون كل ليد."
        ),
        "components": "أردوينو أونو\nشريط ليد WS2812\nمقاومة 330 أوم\nمصدر 5V وأسلاك",
        "wiring": "DIN ← 330 ← الطرف 6\n+5V ← مصدر 5V\nGND ← GND مشترك",
        "code": (
            "#include <Adafruit_NeoPixel.h>\n"
            "#define PIN 6\n"
            "#define N 30\n"
            "Adafruit_NeoPixel strip(N, PIN, NEO_GRB + NEO_KHZ800);\n\n"
            "void setup() { strip.begin(); strip.show(); }\n\n"
            "void loop() {\n"
            "  for (int i = 0; i < N; i++) { strip.setPixelColor(i, strip.Color(255,0,0)); strip.show(); delay(40); }\n"
            "  for (int i = 0; i < N; i++) strip.setPixelColor(i, 0);\n"
            "  strip.show(); delay(200);\n"
            "}\n"
        ),
    },
    {
        "title": "مقدمة NodeMCU ESP8266 (أول برنامج)",
        "video_url": "https://www.youtube.com/watch?v=hbys5W1thwI",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nالتعرّف على لوحة ESP8266 (NodeMCU) — لوحة فيها WiFi — ورفع أول برنامج (وميض الليد المدمج).\n\n"
            "📘 الشرح:\n• ESP8266 أقوى من الأردوينو وفيها WiFi.\n• الليد المدمج بمنطق معكوس (LOW = إضاءة).\n• تحتاج إضافة نواة ESP8266 في Arduino IDE."
        ),
        "components": "لوحة NodeMCU ESP8266\nكابل USB",
        "wiring": "لا يوجد توصيل خارجي — نستخدم الليد المدمج",
        "code": (
            "void setup() { pinMode(LED_BUILTIN, OUTPUT); }\n\n"
            "void loop() {\n"
            "  digitalWrite(LED_BUILTIN, LOW);  delay(500);  // إضاءة (منطق معكوس)\n"
            "  digitalWrite(LED_BUILTIN, HIGH); delay(500);  // إطفاء\n"
            "}\n"
        ),
    },
    {
        "title": "التحكّم عن بعد Blynk + ESP8266 (نسخة ٢)",
        "video_url": "https://www.youtube.com/watch?v=cZVXrwFkN3M",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nشرح إضافي للتحكّم بجهاز من الهاتف عبر الإنترنت باستخدام تطبيق Blynk و ESP8266.\n\n"
            "📘 الشرح:\n• زر في تطبيق Blynk يرسل إشارة عبر الإنترنت.\n• ESP8266 يشغّل الريليه المتّصل."
        ),
        "components": "لوحة NodeMCU ESP8266\nوحدة ريليه\nجهاز كهربائي\nتطبيق Blynk",
        "wiring": "الريليه IN ← الطرف D1\nVCC ← 3V3/5V ، GND ← GND",
        "code": (
            "#define BLYNK_TEMPLATE_ID \"ضع_المعرّف\"\n"
            "#define BLYNK_AUTH_TOKEN  \"ضع_التوكن\"\n"
            "#include <ESP8266WiFi.h>\n"
            "#include <BlynkSimpleEsp8266.h>\n"
            "char ssid[] = \"اسم_الشبكة\";\n"
            "char pass[] = \"كلمة_المرور\";\n"
            "int relay = D1;\n\n"
            "BLYNK_WRITE(V0) { digitalWrite(relay, param.asInt()); }\n\n"
            "void setup() { pinMode(relay, OUTPUT); Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass); }\n\n"
            "void loop() { Blynk.run(); }\n"
        ),
    },
    {
        "title": "ربط ESP8266 بشبكة WiFi وطباعة الـIP",
        "video_url": "https://www.youtube.com/watch?v=nMpfpcEnX6A",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنوصّل ESP8266 بشبكة WiFi ونطبع عنوان IP — أول خطوة لأي مشروع إنترنت أشياء.\n\n"
            "📘 الشرح:\n• WiFi.begin للاتصال بالشبكة.\n• ننتظر حتى WL_CONNECTED ثم نطبع الـIP."
        ),
        "components": "لوحة NodeMCU ESP8266\nكابل USB",
        "wiring": "لا يوجد توصيل خارجي",
        "code": (
            "#include <ESP8266WiFi.h>\n"
            "const char* ssid = \"اسم_الشبكة\";\n"
            "const char* pass = \"كلمة_المرور\";\n\n"
            "void setup() {\n"
            "  Serial.begin(9600); WiFi.begin(ssid, pass);\n"
            "  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print(\".\"); }\n"
            "  Serial.println(); Serial.print(\"IP: \"); Serial.println(WiFi.localIP());\n"
            "}\n\n"
            "void loop() {}\n"
        ),
    },
    {
        "title": "🤖 روبوت يتجنّب العوائق (نسخة ٢)",
        "video_url": "https://www.youtube.com/watch?v=8r_OGwmGHbc",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nشرح إضافي خطوة بخطوة لبناء سيارة روبوت تتفادى العوائق.\n\n"
            "📘 الشرح:\n• HC-SR04 يقيس المسافة، وإن وُجد عائق يتوقّف ويلتفّ.\n• L298N يتحكّم بالمحرّكات."
        ),
        "components": "أردوينو أونو\nهيكل سيارة ومحرّكَي DC\nدرايفر L298N\nحسّاس HC-SR04\nبطارية وأسلاك",
        "wiring": "L298N: IN1←5, IN2←6, IN3←9, IN4←10\nHC-SR04: Trig←A0, Echo←A1",
        "code": (
            "int IN1=5, IN2=6, IN3=9, IN4=10, trig=A0, echo=A1;\n"
            "long distance() {\n"
            "  digitalWrite(trig,LOW); delayMicroseconds(2);\n"
            "  digitalWrite(trig,HIGH); delayMicroseconds(10); digitalWrite(trig,LOW);\n"
            "  return pulseIn(echo,HIGH)*0.034/2;\n"
            "}\n"
            "void fwd(){ digitalWrite(IN1,HIGH);digitalWrite(IN2,LOW);digitalWrite(IN3,HIGH);digitalWrite(IN4,LOW); }\n"
            "void turn(){ digitalWrite(IN1,HIGH);digitalWrite(IN2,LOW);digitalWrite(IN3,LOW);digitalWrite(IN4,HIGH); }\n"
            "void stopM(){ digitalWrite(IN1,LOW);digitalWrite(IN2,LOW);digitalWrite(IN3,LOW);digitalWrite(IN4,LOW); }\n\n"
            "void setup(){ pinMode(IN1,OUTPUT);pinMode(IN2,OUTPUT);pinMode(IN3,OUTPUT);pinMode(IN4,OUTPUT); pinMode(trig,OUTPUT);pinMode(echo,INPUT); }\n\n"
            "void loop(){ if(distance()>20) fwd(); else { stopM(); delay(200); turn(); delay(400); } }\n"
        ),
    },
    {
        "title": "🤖 روبوت ذكي يتجنّب الحواجز (نسخة ٣)",
        "video_url": "https://www.youtube.com/watch?v=1Cp5As4ITkU",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنسخة متقدّمة: عند وجود حاجز يقيس المسافة يميناً ويساراً ويختار الاتجاه الأوسع.\n\n"
            "📘 الشرح:\n• نستخدم سيرفو لتوجيه الحسّاس ومقارنة المسافتين.\n• نفس مبدأ L298N للمحرّكات."
        ),
        "components": "أردوينو أونو\nهيكل سيارة ومحرّكَي DC\nدرايفر L298N\nحسّاس HC-SR04 + سيرفو\nبطارية وأسلاك",
        "wiring": "L298N: IN1←5, IN2←6, IN3←9, IN4←10\nHC-SR04: Trig←A0, Echo←A1\nالسيرفو ← الطرف 3",
        "code": (
            "#include <Servo.h>\n"
            "Servo look; int IN1=5,IN2=6,IN3=9,IN4=10,trig=A0,echo=A1;\n"
            "long dist(){ digitalWrite(trig,LOW);delayMicroseconds(2);digitalWrite(trig,HIGH);delayMicroseconds(10);digitalWrite(trig,LOW); return pulseIn(echo,HIGH)*0.034/2; }\n"
            "void fwd(){ digitalWrite(IN1,HIGH);digitalWrite(IN2,LOW);digitalWrite(IN3,HIGH);digitalWrite(IN4,LOW); }\n"
            "void stopM(){ digitalWrite(IN1,LOW);digitalWrite(IN2,LOW);digitalWrite(IN3,LOW);digitalWrite(IN4,LOW); }\n"
            "void turnR(){ digitalWrite(IN1,HIGH);digitalWrite(IN2,LOW);digitalWrite(IN3,LOW);digitalWrite(IN4,HIGH); }\n"
            "void turnL(){ digitalWrite(IN1,LOW);digitalWrite(IN2,HIGH);digitalWrite(IN3,HIGH);digitalWrite(IN4,LOW); }\n\n"
            "void setup(){ pinMode(IN1,OUTPUT);pinMode(IN2,OUTPUT);pinMode(IN3,OUTPUT);pinMode(IN4,OUTPUT); pinMode(trig,OUTPUT);pinMode(echo,INPUT); look.attach(3); look.write(90); }\n\n"
            "void loop(){\n"
            "  if(dist()>20){ fwd(); return; }\n"
            "  stopM(); look.write(150); delay(300); long l=dist();\n"
            "  look.write(30); delay(300); long r=dist(); look.write(90);\n"
            "  if(l>r) turnL(); else turnR(); delay(400);\n"
            "}\n"
        ),
    },
    {
        "title": "🚗 سيارة روبوت ذكية Smart Car",
        "video_url": "https://www.youtube.com/watch?v=XpEDUQFm6nU",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nبرمجة سيارة روبوت ذكية والتحكّم بحركتها — أساس يمكن تطويره للبلوتوث أو تتبّع الخط.\n\n"
            "📘 الشرح:\n• L298N يتحكّم بمحرّكَي العجلات.\n• دوال جاهزة للأمام/الخلف/يمين/يسار."
        ),
        "components": "أردوينو أونو\nهيكل سيارة ومحرّكَي DC\nدرايفر L298N\nبطارية وأسلاك",
        "wiring": "L298N: IN1←5, IN2←6, IN3←9, IN4←10",
        "code": (
            "int IN1=5,IN2=6,IN3=9,IN4=10;\n"
            "void setM(int a,int b,int c,int d){ digitalWrite(IN1,a);digitalWrite(IN2,b);digitalWrite(IN3,c);digitalWrite(IN4,d); }\n\n"
            "void setup(){ pinMode(IN1,OUTPUT);pinMode(IN2,OUTPUT);pinMode(IN3,OUTPUT);pinMode(IN4,OUTPUT); }\n\n"
            "void loop(){\n"
            "  setM(1,0,1,0); delay(1500);  // أمام\n"
            "  setM(0,0,0,0); delay(500);   // توقف\n"
            "  setM(1,0,0,1); delay(700);   // يمين\n"
            "  setM(0,0,0,0); delay(500);\n"
            "}\n"
        ),
    },
]


def _clean_title(title):
    title = re.sub(r"^مشروع\s*\d+\s*[:：]\s*", "", title)
    title = re.sub(r"^\s*[٠-٩\d]+\)\s*", "", title)
    return title.strip()


def seed_and_renumber(apps, schema_editor):
    EducationalVideo = apps.get_model("store", "EducationalVideo")
    for item in GROUP4:
        EducationalVideo.objects.get_or_create(
            video_url=item["video_url"],
            defaults={k: v for k, v in item.items() if k != "video_url"},
        )
    # إعادة ترقيم الكل بالتسلسل (يملأ أي فراغ من حذف سابق)
    for n, video in enumerate(EducationalVideo.objects.order_by("project_number", "id"), start=1):
        video.project_number = n
        video.title = "مشروع {}: {}".format(n, _clean_title(video.title))
        video.save(update_fields=["project_number", "title"])


def reverse(apps, schema_editor):
    EducationalVideo = apps.get_model("store", "EducationalVideo")
    urls = [p["video_url"] for p in GROUP4]
    EducationalVideo.objects.filter(video_url__in=urls).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0024_group3_and_numbering"),
    ]

    operations = [
        migrations.RunPython(seed_and_renumber, reverse),
    ]
