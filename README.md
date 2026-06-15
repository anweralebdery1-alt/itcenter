# Django E-Commerce Site

موقع متجر إلكتروني Django مرتبط ببرنامج المبيعات الأوفلاين.

## التشغيل المحلي

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

افتح:

```text
http://127.0.0.1:8000/
```

لوحة الإدارة:

```text
http://127.0.0.1:8000/admin/
```

من لوحة الإدارة يمكنك التحكم في:

- إعدادات الموقع: الاسم، الشعار، صورة البانر، ألوان الموقع، رقم الهاتف والواتساب.
- التصنيفات والسلاسل.
- المنتجات، الصور، الوصف، المواصفات JSON، الأسعار، الكميات، والعروض.
- العملاء، رموز OTP، والطلبات وعناصر كل طلب.
- طلبات الدفع عند الاستلام، وتجهيز صفحة ربط الدفع الإلكتروني.

بعد هذا التحديث شغل:

```bash
python manage.py migrate
```

ثم ادخل إلى `/admin/` وافتح `إعدادات الموقع` وأضف الشعار وصورة الواجهة.

## تجربة الشراء

1. من صفحة المنتج اضغط `أضف إلى السلة`.
2. افتح السلة ثم `إكمال الشراء`.
3. اختر طريقة الدفع واكتب رقم الهاتف.
4. سيظهر رمز OTP تجريبي على الصفحة المحلية.
5. بعد إدخال الرمز اكتب الاسم الكامل والمحافظة والعنوان.
6. إذا اخترت الدفع عند الاستلام سيتم تسجيل الطلب مباشرة.
7. إذا اخترت الدفع الإلكتروني ستظهر صفحة تحويل جاهزة للربط مع بوابة دفع حقيقية.

## API المزامنة

هذه endpoints مضافة للمزامنة مع برنامج الأوفلاين:

```text
GET  /api/stock_snapshot/
POST /api/stock_update/
POST /api/sync/push/
```

المفتاح الافتراضي للتجربة:

```text
changeme_token
```

في الإنتاج اضبط متغير البيئة:

```bash
SYNC_API_TOKEN=your-secret-token
```

## تشغيل المزامنة محلياً

1. شغل الموقع:

```bash
python manage.py runserver
```

2. من مجلد برنامج الأوفلاين شغل:

```bash
python sync_integrated.py --run
```

أو استخدم زر المزامنة من تبويب الإعدادات في البرنامج.

## النشر المجاني على Render

ارفع مجلد الموقع إلى GitHub ثم أنشئ Web Service في Render.

الإعدادات المقترحة:

```text
Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
Start Command: gunicorn shop.wsgi:application
```

متغيرات البيئة:

```text
SECRET_KEY=ضع_مفتاح_طويل
DEBUG=False
ALLOWED_HOSTS=your-app-name.onrender.com
SYNC_API_TOKEN=ضع_توكن_سري
```

للتجربة المجانية يمكن استخدام SQLite، لكن عند النقل لاستضافة مدفوعة يفضل PostgreSQL. المشروع يدعم `DATABASE_URL` عند إضافته من مزود الاستضافة.

## ملاحظات مهمة

- قاعدة الأوفلاين الحالية هي المصدر الأساسي للمنتجات والمخزون.
- لا تحذف `store.db` أو `db.sqlite3` بدون نسخة احتياطية.
- قاعدة الأوفلاين تحتوي حالياً SKU مكرر، لذلك تستخدم المزامنة `id` المحلي كمفتاح المنتج في الموقع لتجنب التكرار.
