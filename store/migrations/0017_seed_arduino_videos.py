from django.db import migrations


VIDEOS = [
    {
        "title": "١) تشغيل ثنائي ضوئي (LED) — أول مشروع أردوينو",
        "video_url": "https://www.youtube.com/watch?v=fJWR7dBuc18",
        "source": "toptechboy (Paul McWhorter)",
        "description": (
            "أبسط مشروع للبدء مع الأردوينو: نجعل LED يومض كل ثانية.\n"
            "تتعلّم فيه: توصيل LED، استخدام مقاومة الحماية، والدوال pinMode و digitalWrite و delay."
        ),
        "components": "أردوينو أونو (Arduino Uno)\nثنائي ضوئي LED\nمقاومة 220 أوم\nلوحة تجارب (Breadboard)\nأسلاك توصيل",
        "code": (
            "void setup() {\n"
            "  pinMode(13, OUTPUT);   // نجعل الطرف 13 مخرجاً\n"
            "}\n\n"
            "void loop() {\n"
            "  digitalWrite(13, HIGH);  // تشغيل الـ LED\n"
            "  delay(1000);             // انتظر ثانية\n"
            "  digitalWrite(13, LOW);   // إطفاء الـ LED\n"
            "  delay(1000);             // انتظر ثانية\n"
            "}\n"
        ),
    },
    {
        "title": "٢) التحكّم بـ LED عبر زر ضاغط",
        "video_url": "https://www.youtube.com/watch?v=ZoaUlquC6x8",
        "source": "YouTube Tutorial",
        "description": (
            "نتعلّم قراءة حالة زر ضاغط وتشغيل/إطفاء LED بناءً عليه.\n"
            "المفاهيم: المدخلات digitalRead، الجملة الشرطية if، ومقاومة السحب للأسفل (pull-down)."
        ),
        "components": "أردوينو أونو\nثنائي ضوئي LED\nزر ضاغط (Push Button)\nمقاومة 220 أوم (للـ LED)\nمقاومة 10 كيلو أوم (للزر)\nلوحة تجارب وأسلاك",
        "code": (
            "const int buttonPin = 2;   // طرف الزر\n"
            "const int ledPin = 13;     // طرف الـ LED\n\n"
            "void setup() {\n"
            "  pinMode(ledPin, OUTPUT);\n"
            "  pinMode(buttonPin, INPUT);\n"
            "}\n\n"
            "void loop() {\n"
            "  int state = digitalRead(buttonPin);\n"
            "  if (state == HIGH) {\n"
            "    digitalWrite(ledPin, HIGH);   // الزر مضغوط → تشغيل\n"
            "  } else {\n"
            "    digitalWrite(ledPin, LOW);    // غير مضغوط → إطفاء\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "title": "٣) التحكّم بإضاءة LED عبر مقاومة متغيّرة (PWM)",
        "video_url": "https://www.youtube.com/watch?v=wfjIU_YGmZE",
        "source": "YouTube Tutorial",
        "description": (
            "نتحكّم بشدّة إضاءة LED بتدوير مقاومة متغيّرة.\n"
            "المفاهيم: القراءة التماثلية analogRead، الدالة map، والإخراج بنظام PWM عبر analogWrite."
        ),
        "components": "أردوينو أونو\nثنائي ضوئي LED\nمقاومة متغيّرة 10 كيلو أوم (Potentiometer)\nمقاومة 220 أوم\nلوحة تجارب وأسلاك",
        "code": (
            "const int potPin = A0;   // المقاومة المتغيّرة\n"
            "const int ledPin = 9;    // طرف PWM (~)\n\n"
            "void setup() {\n"
            "  pinMode(ledPin, OUTPUT);\n"
            "}\n\n"
            "void loop() {\n"
            "  int value = analogRead(potPin);              // 0 - 1023\n"
            "  int brightness = map(value, 0, 1023, 0, 255); // 0 - 255\n"
            "  analogWrite(ledPin, brightness);\n"
            "  delay(10);\n"
            "}\n"
        ),
    },
    {
        "title": "٤) قياس المسافة بحسّاس الموجات فوق الصوتية HC-SR04",
        "video_url": "https://www.youtube.com/watch?v=SIc6zj06bhQ",
        "source": "YouTube Tutorial",
        "description": (
            "نقيس المسافة إلى جسم أمام الحسّاس ونعرضها على الشاشة التسلسلية (Serial Monitor).\n"
            "المفاهيم: إرسال نبضة trig، قياس زمن الصدى بـ pulseIn، وحساب المسافة."
        ),
        "components": "أردوينو أونو\nحسّاس المسافة HC-SR04\nلوحة تجارب وأسلاك توصيل",
        "code": (
            "const int trigPin = 9;\n"
            "const int echoPin = 10;\n"
            "long duration;\n"
            "int distance;\n\n"
            "void setup() {\n"
            "  pinMode(trigPin, OUTPUT);\n"
            "  pinMode(echoPin, INPUT);\n"
            "  Serial.begin(9600);\n"
            "}\n\n"
            "void loop() {\n"
            "  digitalWrite(trigPin, LOW);\n"
            "  delayMicroseconds(2);\n"
            "  digitalWrite(trigPin, HIGH);\n"
            "  delayMicroseconds(10);\n"
            "  digitalWrite(trigPin, LOW);\n\n"
            "  duration = pulseIn(echoPin, HIGH);\n"
            "  distance = duration * 0.034 / 2;   // بالسنتيمتر\n\n"
            "  Serial.print(\"Distance: \");\n"
            "  Serial.print(distance);\n"
            "  Serial.println(\" cm\");\n"
            "  delay(500);\n"
            "}\n"
        ),
    },
    {
        "title": "٥) تحريك محرّك سيرفو (Servo Sweep)",
        "video_url": "https://www.youtube.com/watch?v=g9pc6NE0VtM",
        "source": "YouTube Tutorial",
        "description": (
            "نحرّك محرّك سيرفو من 0 إلى 180 درجة ذهاباً وإياباً.\n"
            "المفاهيم: مكتبة Servo، الدوال attach و write، وحلقة for."
        ),
        "components": "أردوينو أونو\nمحرّك سيرفو SG90\nأسلاك توصيل\n(يُفضّل مصدر طاقة خارجي 5 فولت للمحرّكات الأكبر)",
        "code": (
            "#include <Servo.h>\n"
            "Servo myServo;\n\n"
            "void setup() {\n"
            "  myServo.attach(9);   // طرف إشارة السيرفو\n"
            "}\n\n"
            "void loop() {\n"
            "  for (int pos = 0; pos <= 180; pos++) {\n"
            "    myServo.write(pos);\n"
            "    delay(15);\n"
            "  }\n"
            "  for (int pos = 180; pos >= 0; pos--) {\n"
            "    myServo.write(pos);\n"
            "    delay(15);\n"
            "  }\n"
            "}\n"
        ),
    },
]


def seed(apps, schema_editor):
    EducationalVideo = apps.get_model("store", "EducationalVideo")
    for item in VIDEOS:
        EducationalVideo.objects.get_or_create(title=item["title"], defaults=item)


def unseed(apps, schema_editor):
    EducationalVideo = apps.get_model("store", "EducationalVideo")
    EducationalVideo.objects.filter(title__in=[v["title"] for v in VIDEOS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0016_educationalvideo_code_educationalvideo_components_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
