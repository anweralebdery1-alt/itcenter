# -*- coding: utf-8 -*-
from django.db import migrations


AR = "شرح عربي"
EN = "شرح إنجليزي"

PROJECTS = [
    {
        "title": "٦) الليد ثلاثي الألوان RGB",
        "video_url": "https://www.youtube.com/watch?v=cPXpWqHulQA",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنُنتج أي لون بمزج ثلاثة ألوان (أحمر/أخضر/أزرق) بنِسَب مختلفة عبر PWM.\n\n"
            "📘 الشرح:\n• كل لون على طرف PWM مستقل.\n• analogWrite(0–255) يضبط شدّة كل لون.\n• بمزج الشدّات نحصل على ملايين الألوان."
        ),
        "components": "أردوينو أونو\nليد RGB (كاثود مشترك)\n3 مقاومات 220 أوم\nلوحة تجارب وأسلاك",
        "wiring": "الطرف الأحمر ← مقاومة 220 ← الطرف 9\nالطرف الأخضر ← مقاومة 220 ← الطرف 10\nالطرف الأزرق ← مقاومة 220 ← الطرف 11\nالطرف المشترك ← GND",
        "code": (
            "int R = 9, G = 10, B = 11;\n\n"
            "void setColor(int r, int g, int b) {\n"
            "  analogWrite(R, r); analogWrite(G, g); analogWrite(B, b);\n"
            "}\n\n"
            "void setup() {\n"
            "  pinMode(R, OUTPUT); pinMode(G, OUTPUT); pinMode(B, OUTPUT);\n"
            "}\n\n"
            "void loop() {\n"
            "  setColor(255, 0, 0); delay(700);   // أحمر\n"
            "  setColor(0, 255, 0); delay(700);   // أخضر\n"
            "  setColor(0, 0, 255); delay(700);   // أزرق\n"
            "  setColor(255, 255, 0); delay(700); // أصفر\n"
            "  setColor(0, 255, 255); delay(700); // سماوي\n"
            "  setColor(255, 0, 255); delay(700); // بنفسجي\n"
            "}\n"
        ),
    },
    {
        "title": "٧) إشارة المرور بثلاثة ليدات",
        "video_url": "https://www.youtube.com/watch?v=u9wEbo1WNnU",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nمحاكاة إشارة مرور بثلاثة ليدات (أحمر، أصفر، أخضر) بتسلسل زمني.\n\n"
            "📘 الشرح:\n• نشغّل كل ليد لمدّة محدّدة ثم ننتقل للتالي عبر delay.\n• أساس فهم التتابع الزمني في البرمجة."
        ),
        "components": "أردوينو أونو\n3 ليدات (أحمر/أصفر/أخضر)\n3 مقاومات 220 أوم\nلوحة تجارب وأسلاك",
        "wiring": "الأحمر ← 220 ← الطرف 8\nالأصفر ← 220 ← الطرف 9\nالأخضر ← 220 ← الطرف 10\nالأطراف السالبة ← GND",
        "code": (
            "int red = 8, yellow = 9, green = 10;\n\n"
            "void setup() {\n"
            "  pinMode(red, OUTPUT); pinMode(yellow, OUTPUT); pinMode(green, OUTPUT);\n"
            "}\n\n"
            "void loop() {\n"
            "  digitalWrite(red, HIGH); delay(3000); digitalWrite(red, LOW);\n"
            "  digitalWrite(green, HIGH); delay(3000); digitalWrite(green, LOW);\n"
            "  digitalWrite(yellow, HIGH); delay(1000); digitalWrite(yellow, LOW);\n"
            "}\n"
        ),
    },
    {
        "title": "٨) حسّاس الحركة PIR + إضاءة تلقائية",
        "video_url": "https://www.youtube.com/watch?v=k4xN8LyN4Y4",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنكتشف حركة الأشخاص عبر حسّاس PIR ونشغّل ليداً (أو جهازاً) تلقائياً — أساس أنظمة الإنذار والإضاءة الذكية.\n\n"
            "📘 الشرح:\n• PIR يعطي HIGH عند اكتشاف حركة.\n• نقرأه بـ digitalRead ونشغّل المخرج."
        ),
        "components": "أردوينو أونو\nحسّاس حركة PIR (HC-SR501)\nليد + مقاومة 220 أوم\nأسلاك توصيل",
        "wiring": "VCC ← 5V\nGND ← GND\nOUT ← الطرف 2\nليد ← 220 ← الطرف 13",
        "code": (
            "int pir = 2, led = 13;\n\n"
            "void setup() {\n"
            "  pinMode(pir, INPUT); pinMode(led, OUTPUT); Serial.begin(9600);\n"
            "}\n\n"
            "void loop() {\n"
            "  if (digitalRead(pir) == HIGH) {\n"
            "    digitalWrite(led, HIGH); Serial.println(\"Motion detected\");\n"
            "  } else {\n"
            "    digitalWrite(led, LOW);\n"
            "  }\n"
            "  delay(200);\n"
            "}\n"
        ),
    },
    {
        "title": "٩) حسّاس الإضاءة LDR (مصباح ليلي تلقائي)",
        "video_url": "https://www.youtube.com/watch?v=3YGBsfvjS8g",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنقيس مستوى الضوء بمقاومة ضوئية LDR ونشغّل الإضاءة عند الظلام تلقائياً.\n\n"
            "📘 الشرح:\n• analogRead يقرأ الجهد (0–1023) حسب شدّة الضوء.\n• نقارنه بحدّ عتبة ونتحكّم بالليد."
        ),
        "components": "أردوينو أونو\nمقاومة ضوئية LDR\nمقاومة 10 كيلو أوم\nليد + مقاومة 220 أوم\nأسلاك",
        "wiring": "LDR بين 5V و A0\nمقاومة 10 كيلو بين A0 و GND\nليد ← 220 ← الطرف 13",
        "code": (
            "int ldr = A0, led = 13;\n\n"
            "void setup() {\n"
            "  pinMode(led, OUTPUT); Serial.begin(9600);\n"
            "}\n\n"
            "void loop() {\n"
            "  int light = analogRead(ldr);\n"
            "  Serial.println(light);\n"
            "  if (light < 400) digitalWrite(led, HIGH);  // ظلام → أضئ\n"
            "  else digitalWrite(led, LOW);\n"
            "  delay(200);\n"
            "}\n"
        ),
    },
    {
        "title": "١٠) استقبال ريموت بالأشعة تحت الحمراء IR",
        "video_url": "https://www.youtube.com/watch?v=NVrY8-xTD8g",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنقرأ أكواد أزرار أي ريموت IR لنتحكّم بالأجهزة عن بُعد.\n\n"
            "📘 الشرح:\n• مستقبل IR يلتقط إشارة الريموت.\n• مكتبة IRremote تفكّ الكود ونطبعه لمعرفة كل زر.\n• تحتاج تثبيت مكتبة IRremote."
        ),
        "components": "أردوينو أونو\nمستقبل IR (VS1838B)\nريموت تحكّم\nأسلاك",
        "wiring": "OUT ← الطرف 11\nVCC ← 5V\nGND ← GND",
        "code": (
            "#include <IRremote.h>\n"
            "int RECV = 11;\n"
            "IRrecv irrecv(RECV);\n"
            "decode_results results;\n\n"
            "void setup() {\n"
            "  Serial.begin(9600); irrecv.enableIRIn();\n"
            "}\n\n"
            "void loop() {\n"
            "  if (irrecv.decode(&results)) {\n"
            "    Serial.println(results.value, HEX);  // كود الزر المضغوط\n"
            "    irrecv.resume();\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "title": "١١) شاشة LCD مقاس 16×2 عبر I2C",
        "video_url": "https://www.youtube.com/watch?v=TDQF1ZoJzt8",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنكتب نصوصاً وقيماً على شاشة LCD باستخدام وحدة I2C (سلكان فقط للبيانات).\n\n"
            "📘 الشرح:\n• وحدة I2C تقلّل الأسلاك من 6 إلى سلكين (SDA/SCL).\n• مكتبة LiquidCrystal_I2C للكتابة.\n• العنوان غالباً 0x27 (قد يكون 0x3F)."
        ),
        "components": "أردوينو أونو\nشاشة LCD 16×2 مع وحدة I2C\nأسلاك",
        "wiring": "SDA ← A4\nSCL ← A5\nVCC ← 5V\nGND ← GND",
        "code": (
            "#include <LiquidCrystal_I2C.h>\n"
            "LiquidCrystal_I2C lcd(0x27, 16, 2);\n\n"
            "void setup() {\n"
            "  lcd.init(); lcd.backlight();\n"
            "  lcd.setCursor(0, 0); lcd.print(\"IT Center\");\n"
            "  lcd.setCursor(0, 1); lcd.print(\"Hello Arduino\");\n"
            "}\n\n"
            "void loop() {\n"
            "}\n"
        ),
    },
    {
        "title": "١٢) التحكّم بليد عبر البلوتوث HC-05",
        "video_url": "https://www.youtube.com/watch?v=UaojRqKBHW0",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنتحكّم بجهاز من الهاتف عبر البلوتوث — أساس المشاريع اللاسلكية والسيارات.\n\n"
            "📘 الشرح:\n• وحدة HC-05 تستقبل أوامر من تطبيق بلوتوث على الهاتف.\n• نقرأ الحرف الوارد ونشغّل/نطفئ.\n• نستخدم SoftwareSerial لتجنّب تعارض منفذ USB."
        ),
        "components": "أردوينو أونو\nوحدة بلوتوث HC-05\nليد + مقاومة 220 أوم\nأسلاك",
        "wiring": "HC-05 TX ← الطرف 2\nHC-05 RX ← الطرف 3\nVCC ← 5V ، GND ← GND\nليد ← 220 ← الطرف 13",
        "code": (
            "#include <SoftwareSerial.h>\n"
            "SoftwareSerial BT(2, 3);  // RX, TX\n"
            "int led = 13;\n\n"
            "void setup() {\n"
            "  BT.begin(9600); pinMode(led, OUTPUT);\n"
            "}\n\n"
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
        "title": "١٣) حسّاس ركن السيارة (تنبيه بالمسافة)",
        "video_url": "https://www.youtube.com/watch?v=j4tU-7Uzutc",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنطلق صوتاً يتسارع كلّما اقترب جسم — مثل حسّاسات ركن السيارات.\n\n"
            "📘 الشرح:\n• HC-SR04 يقيس المسافة.\n• نغيّر إيقاع صوت البازر حسب قُرب الجسم عبر tone/noTone."
        ),
        "components": "أردوينو أونو\nحسّاس HC-SR04\nبازر (Buzzer)\nأسلاك",
        "wiring": "Trig ← الطرف 9\nEcho ← الطرف 10\nBuzzer ← الطرف 8 و GND\nVCC/GND للحسّاس",
        "code": (
            "int trig = 9, echo = 10, buzzer = 8;\n\n"
            "void setup() {\n"
            "  pinMode(trig, OUTPUT); pinMode(echo, INPUT); pinMode(buzzer, OUTPUT);\n"
            "  Serial.begin(9600);\n"
            "}\n\n"
            "void loop() {\n"
            "  digitalWrite(trig, LOW); delayMicroseconds(2);\n"
            "  digitalWrite(trig, HIGH); delayMicroseconds(10); digitalWrite(trig, LOW);\n"
            "  long d = pulseIn(echo, HIGH) * 0.034 / 2;\n"
            "  Serial.println(d);\n"
            "  if (d < 10) { tone(buzzer, 1000); }                 // قريب جداً: صوت مستمر\n"
            "  else if (d < 30) { tone(buzzer, 1000); delay(100); noTone(buzzer); delay(100); }\n"
            "  else { noTone(buzzer); }\n"
            "}\n"
        ),
    },
    {
        "title": "١٤) 🤖 روبوت يتجنّب العوائق",
        "video_url": "https://www.youtube.com/watch?v=d_eMlOelpD0",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nسيارة روبوت تسير للأمام وتلتفّ تلقائياً عند وجود عائق — أشهر مشاريع الروبوت.\n\n"
            "📘 الشرح:\n• HC-SR04 يقيس المسافة أمام الروبوت.\n• إن كان الطريق خالياً يتقدّم، وإلا يتوقّف ويلتفّ.\n• درايفر L298N يتحكّم بمحرّكَي العجلات."
        ),
        "components": "أردوينو أونو\nهيكل سيارة بعجلات ومحرّكَي DC\nدرايفر محرّكات L298N\nحسّاس HC-SR04\nمحرّك سيرفو SG90\nبطارية وأسلاك",
        "wiring": "L298N: IN1←5, IN2←6, IN3←9, IN4←10\nالمحرّكات على OUT1/2 و OUT3/4\nHC-SR04: Trig←A0, Echo←A1\nسيرفو ← الطرف 3\nتغذية L298N من البطارية و GND مشترك",
        "code": (
            "#include <Servo.h>\n"
            "Servo look;\n"
            "int IN1 = 5, IN2 = 6, IN3 = 9, IN4 = 10;\n"
            "int trig = A0, echo = A1;\n\n"
            "long distance() {\n"
            "  digitalWrite(trig, LOW); delayMicroseconds(2);\n"
            "  digitalWrite(trig, HIGH); delayMicroseconds(10); digitalWrite(trig, LOW);\n"
            "  return pulseIn(echo, HIGH) * 0.034 / 2;\n"
            "}\n"
            "void forward() { digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW); digitalWrite(IN3,HIGH); digitalWrite(IN4,LOW); }\n"
            "void stopM()   { digitalWrite(IN1,LOW);  digitalWrite(IN2,LOW); digitalWrite(IN3,LOW);  digitalWrite(IN4,LOW); }\n"
            "void turn()    { digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW); digitalWrite(IN3,LOW);  digitalWrite(IN4,HIGH); }\n\n"
            "void setup() {\n"
            "  pinMode(IN1,OUTPUT); pinMode(IN2,OUTPUT); pinMode(IN3,OUTPUT); pinMode(IN4,OUTPUT);\n"
            "  pinMode(trig,OUTPUT); pinMode(echo,INPUT);\n"
            "  look.attach(3); look.write(90);\n"
            "}\n\n"
            "void loop() {\n"
            "  if (distance() > 20) forward();\n"
            "  else { stopM(); delay(200); turn(); delay(400); }\n"
            "}\n"
        ),
    },
    {
        "title": "١٥) 🚗 سيارة روبوت بالتحكّم عبر البلوتوث",
        "video_url": "https://www.youtube.com/watch?v=iaSibLljmgU",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنقود سيارة روبوت من تطبيق على الهاتف عبر البلوتوث (أمام/خلف/يمين/يسار).\n\n"
            "📘 الشرح:\n• تطبيق البلوتوث يرسل حرفاً لكل اتجاه (F/B/L/R).\n• نقرأ الحرف ونتحكّم بالمحرّكات عبر L298N."
        ),
        "components": "أردوينو أونو\nهيكل سيارة بعجلات ومحرّكَي DC\nدرايفر L298N\nوحدة بلوتوث HC-05\nبطارية وأسلاك",
        "wiring": "L298N: IN1←5, IN2←6, IN3←9, IN4←10\nHC-05: TX←الطرف 2، RX←الطرف 3\nتغذية وGND مشترك",
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
            "    if (c == 'F') setM(1,0,1,0);       // أمام\n"
            "    else if (c == 'B') setM(0,1,0,1);  // خلف\n"
            "    else if (c == 'L') setM(0,1,1,0);  // يسار\n"
            "    else if (c == 'R') setM(1,0,0,1);  // يمين\n"
            "    else setM(0,0,0,0);                // توقف\n"
            "  }\n"
            "}\n"
        ),
    },
    {
        "title": "١٦) 🛣️ روبوت تتبّع الخط (Line Follower)",
        "video_url": "https://www.youtube.com/watch?v=2PA0f5edKsM",
        "source": EN,
        "description": (
            "🎯 الفكرة والهدف:\nروبوت يتبع خطاً على الأرض تلقائياً باستخدام حسّاسَي أشعة تحت حمراء.\n\n"
            "📘 الشرح:\n• كل حسّاس IR يميّز الخط (أسود) عن الأرضية (أبيض).\n• حسب قراءة الحسّاسين نصحّح اتجاه العجلات عبر L298N."
        ),
        "components": "أردوينو أونو\nهيكل سيارة بعجلات ومحرّكَي DC\nدرايفر L298N\nحسّاسا تتبّع خط IR\nبطارية وأسلاك",
        "wiring": "L298N: IN1←5, IN2←6, IN3←9, IN4←10\nحسّاس IR الأيمن ← الطرف 2\nحسّاس IR الأيسر ← الطرف 4",
        "code": (
            "int IN1 = 5, IN2 = 6, IN3 = 9, IN4 = 10;\n"
            "int rightIR = 2, leftIR = 4;\n\n"
            "void fwd()   { digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW); digitalWrite(IN3,HIGH); digitalWrite(IN4,LOW); }\n"
            "void right() { digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW); digitalWrite(IN3,LOW);  digitalWrite(IN4,LOW); }\n"
            "void left()  { digitalWrite(IN1,LOW);  digitalWrite(IN2,LOW); digitalWrite(IN3,HIGH); digitalWrite(IN4,LOW); }\n"
            "void stopM() { digitalWrite(IN1,LOW);  digitalWrite(IN2,LOW); digitalWrite(IN3,LOW);  digitalWrite(IN4,LOW); }\n\n"
            "void setup() {\n"
            "  pinMode(IN1,OUTPUT); pinMode(IN2,OUTPUT); pinMode(IN3,OUTPUT); pinMode(IN4,OUTPUT);\n"
            "  pinMode(rightIR,INPUT); pinMode(leftIR,INPUT);\n"
            "}\n\n"
            "void loop() {\n"
            "  int r = digitalRead(rightIR), l = digitalRead(leftIR);\n"
            "  if (l == 0 && r == 0) fwd();        // كلاهما على الخط\n"
            "  else if (l == 1 && r == 0) left();  // انحرف يساراً\n"
            "  else if (l == 0 && r == 1) right(); // انحرف يميناً\n"
            "  else stopM();\n"
            "}\n"
        ),
    },
    {
        "title": "١٧) 🌐 إنترنت الأشياء: التحكّم بليد عبر WiFi (ESP8266)",
        "video_url": "https://www.youtube.com/watch?v=XOAlfEtyRsk",
        "source": AR,
        "description": (
            "🎯 الفكرة والهدف:\nنتحكّم بجهاز من أي متصفّح عبر شبكة WiFi باستخدام NodeMCU ESP8266 — مدخل إنترنت الأشياء.\n\n"
            "📘 الشرح:\n• ESP8266 يتصل بالشبكة ويشغّل خادم ويب صغيراً.\n• فتح /on أو /off من المتصفّح يشغّل/يطفئ الليد.\n• تحتاج مكتبة ESP8266 في Arduino IDE."
        ),
        "components": "لوحة NodeMCU ESP8266\nليد + مقاومة 220 أوم\nأسلاك",
        "wiring": "ليد ← 220 ← الطرف D1\nالطرف السالب ← GND",
        "code": (
            "#include <ESP8266WiFi.h>\n"
            "#include <ESP8266WebServer.h>\n"
            "const char* ssid = \"اسم_الشبكة\";\n"
            "const char* pass = \"كلمة_المرور\";\n"
            "ESP8266WebServer server(80);\n"
            "int led = D1;\n\n"
            "void handleOn()  { digitalWrite(led, HIGH); server.send(200, \"text/plain\", \"LED ON\"); }\n"
            "void handleOff() { digitalWrite(led, LOW);  server.send(200, \"text/plain\", \"LED OFF\"); }\n\n"
            "void setup() {\n"
            "  pinMode(led, OUTPUT); Serial.begin(9600);\n"
            "  WiFi.begin(ssid, pass);\n"
            "  while (WiFi.status() != WL_CONNECTED) { delay(500); }\n"
            "  Serial.println(WiFi.localIP());\n"
            "  server.on(\"/on\", handleOn); server.on(\"/off\", handleOff);\n"
            "  server.begin();\n"
            "}\n\n"
            "void loop() { server.handleClient(); }\n"
        ),
    },
    {
        "title": "١٨) 🏠 مقبس ذكي: تحكّم بجهاز كهربائي عبر تطبيق Blynk",
        "video_url": "https://www.youtube.com/watch?v=7lZ0DXKHR_U",
        "source": EN,
        "description": (
            "🎯 الفكرة والهدف:\nنتحكّم بجهاز كهربائي (مصباح/مروحة) من الهاتف عبر الإنترنت باستخدام ريليه و ESP8266 وتطبيق Blynk.\n\n"
            "📘 الشرح:\n• Blynk تطبيق جاهز يعطيك زراً في الهاتف.\n• عند الضغط يرسل إشارة عبر الإنترنت لـ ESP8266 فيشغّل الريليه.\n⚠️ الريليه يتعامل مع الكهرباء المنزلية — انتبه للسلامة."
        ),
        "components": "لوحة NodeMCU ESP8266\nوحدة ريليه (Relay)\nجهاز كهربائي\nأسلاك\nتطبيق Blynk على الهاتف",
        "wiring": "الريليه IN ← الطرف D1\nVCC ← 3V3/5V ، GND ← GND",
        "code": (
            "#define BLYNK_TEMPLATE_ID \"ضع_المعرّف\"\n"
            "#define BLYNK_AUTH_TOKEN  \"ضع_التوكن\"\n"
            "#include <ESP8266WiFi.h>\n"
            "#include <BlynkSimpleEsp8266.h>\n"
            "char ssid[] = \"اسم_الشبكة\";\n"
            "char pass[] = \"كلمة_المرور\";\n"
            "int relay = D1;\n\n"
            "BLYNK_WRITE(V0) { digitalWrite(relay, param.asInt()); }  // زر التطبيق\n\n"
            "void setup() {\n"
            "  pinMode(relay, OUTPUT);\n"
            "  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);\n"
            "}\n\n"
            "void loop() { Blynk.run(); }\n"
        ),
    },
    {
        "title": "١٩) 🏡 أتمتة منزل: التحكّم بأربعة أجهزة عبر WiFi",
        "video_url": "https://www.youtube.com/watch?v=fRCVx6yKoYw",
        "source": EN,
        "description": (
            "🎯 الفكرة والهدف:\nنظام منزل ذكي يتحكّم بأربعة أجهزة من الهاتف عبر Blynk و ESP8266.\n\n"
            "📘 الشرح:\n• أربعة أزرار في تطبيق Blynk (V0–V3) لكل جهاز ريليه.\n• قابل للتوسعة لغرف كاملة.\n⚠️ عند العمل مع الكهرباء المنزلية اتّبع إجراءات السلامة."
        ),
        "components": "لوحة NodeMCU ESP8266\nوحدة 4 ريليه\nأجهزة كهربائية\nأسلاك\nتطبيق Blynk",
        "wiring": "الريليهات ← D1, D2, D3, D4\nVCC ← 5V ، GND ← GND مشترك",
        "code": (
            "#include <ESP8266WiFi.h>\n"
            "#include <BlynkSimpleEsp8266.h>\n"
            "char auth[] = \"التوكن\";\n"
            "char ssid[] = \"الشبكة\";\n"
            "char pass[] = \"المرور\";\n"
            "int relays[4] = {D1, D2, D3, D4};\n\n"
            "BLYNK_WRITE(V0) { digitalWrite(relays[0], param.asInt()); }\n"
            "BLYNK_WRITE(V1) { digitalWrite(relays[1], param.asInt()); }\n"
            "BLYNK_WRITE(V2) { digitalWrite(relays[2], param.asInt()); }\n"
            "BLYNK_WRITE(V3) { digitalWrite(relays[3], param.asInt()); }\n\n"
            "void setup() {\n"
            "  for (int i = 0; i < 4; i++) pinMode(relays[i], OUTPUT);\n"
            "  Blynk.begin(auth, ssid, pass);\n"
            "}\n\n"
            "void loop() { Blynk.run(); }\n"
        ),
    },
]


def seed(apps, schema_editor):
    EducationalVideo = apps.get_model("store", "EducationalVideo")
    # حذف الفيديوهات المختصرة (بلا كود) والإبقاء على الكاملة
    EducationalVideo.objects.filter(code="").delete()
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
        ("store", "0020_seed_arabic_videos"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
