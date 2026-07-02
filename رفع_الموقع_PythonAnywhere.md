# رفع الموقع على PythonAnywhere (مجاني — للمرحلة التجريبية)

اخترنا **PythonAnywhere** لأنه:
- مجاني بلا بطاقة ائتمان.
- **يحفظ قاعدة البيانات SQLite والصور بشكل دائم** (لا تُمسح عند إعادة التشغيل — بعكس Render المجاني).
- يعطيك رابطاً عاماً `https://USERNAME.pythonanywhere.com` يستقبل المزامنة من برنامج الأوفلاين.

> لاحقاً عند شراء دومين واستضافة، ننقل نفس المشروع بسهولة.

---

## 1) أنشئ حساباً مجانياً
ادخل https://www.pythonanywhere.com → Create a Beginner account.

## 2) ارفع ملفات المشروع
من تبويب **Files** أو **Consoles → Bash**:
- الأسهل: ارفع مجلد `ecommerce_site_package` كملف ZIP ثم فك ضغطه:
  ```bash
  unzip ecommerce_site_package.zip
  ```
  أو إن كان عندك Git:
  ```bash
  git clone <رابط-المستودع>
  ```

## 3) بيئة افتراضية وتنصيب المتطلبات
في Bash console:
```bash
cd ~/ecommerce_site_package
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4) متغيّرات البيئة والإعداد
ولّد مفتاحاً سرياً:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```
ثم جهّز قاعدة البيانات والملفات الساكنة:
```bash
export DEBUG=False
export ALLOWED_HOSTS=USERNAME.pythonanywhere.com
export SECRET_KEY="المفتاح-الذي-ولّدته"
export SYNC_API_TOKEN="اختر-رمزاً-سرياً-قوياً"
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser   # لحساب لوحة الإدارة
```

## 5) أنشئ تطبيق الويب
تبويب **Web → Add a new web app → Manual configuration → Python 3.10**.
ثم اضبط:
- **Source code:** `/home/USERNAME/ecommerce_site_package`
- **Virtualenv:** `/home/USERNAME/ecommerce_site_package/venv`

عدّل ملف **WSGI** (رابطه في صفحة Web) ليصبح:
```python
import os, sys
path = '/home/USERNAME/ecommerce_site_package'
if path not in sys.path:
    sys.path.append(path)
os.environ['DJANGO_SETTINGS_MODULE'] = 'shop.settings'
os.environ['DEBUG'] = 'False'
os.environ['ALLOWED_HOSTS'] = 'USERNAME.pythonanywhere.com'
os.environ['SECRET_KEY'] = 'نفس-المفتاح'
os.environ['SYNC_API_TOKEN'] = 'نفس-الرمز-السري'
os.environ['SHOW_OTP'] = 'True'   # حل OTP المؤقت (يظهر الرمز على الشاشة)
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## 6) مسارات الملفات الساكنة والوسائط (تبويب Web → Static files)
| URL | Directory |
|-----|-----------|
| `/static/` | `/home/USERNAME/ecommerce_site_package/staticfiles` |
| `/media/`  | `/home/USERNAME/ecommerce_site_package/media` |

## 7) شغّل
اضغط **Reload** في تبويب Web، ثم افتح `https://USERNAME.pythonanywhere.com`.
لوحة الإدارة: `/admin`.

## 8) اربط برنامج الأوفلاين بالموقع المرفوع
في برنامج الأوفلاين → الإعدادات:
- **عنوان الموقع:** `https://USERNAME.pythonanywhere.com`
- **رمز المزامنة:** نفس `SYNC_API_TOKEN` أعلاه.
ثم اضغط «مزامنة الآن».

---

## ملاحظات
- **OTP للإنتاج:** اضبط `OTPIQ_API_KEY` و`SHOW_OTP=False` حتى يصل الرمز عبر OTPIQ ولا يظهر على الشاشة.
- **الصور:** تُخدَم من `/media/` (مهيّأ في الإعدادات).
- **الأمان:** اضبط `SYNC_API_TOKEN` بقيمة قوية ومطابقة لقيمة برنامج الأوفلاين.
- **النسخ الاحتياطي:** نزّل `db.sqlite3` ومجلد `media/` دورياً من تبويب Files.
