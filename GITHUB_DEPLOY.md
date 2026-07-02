# دورة تحديث الموقع عبر GitHub

المصدر الأساسي للموقع هو هذا المجلد المحلي. لا نعدل ملفات Python أو القوالب
مباشرة على خادم Contabo. التسلسل المعتمد هو:

1. تعديل الموقع محليًا.
2. تشغيل الفحوصات والاختبارات.
3. رفع التغيير إلى فرع `main` في GitHub.
4. سحب `main` على Contabo وتشغيل النشر.

## شرط أمني

يجب أن يكون المستودع `anweralebdery1-alt/itcenter` خاصًا `Private` قبل أول
عملية رفع. ملف البيئة الحقيقي يبقى فقط في `/etc/itcenterstore.env` على الخادم،
ولا يُرفع إلى GitHub مطلقًا. كذلك لا تُرفع قواعد البيانات أو مجلد `media`.

لتحويل المستودع: افتح صفحة المستودع في GitHub ثم:

`Settings > General > Danger Zone > Change repository visibility > Private`

## رفع تعديل من الحاسبة

من PowerShell داخل مجلد الموقع:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish.ps1 `
  -Message "وصف مختصر للتعديل" `
  -PrivateRepositoryConfirmed
```

السكربت يرفض الرفع إذا فشلت اختبارات Django، أو وُجد migration غير منشأ، أو
كانت قاعدة بيانات أو مفاتيح سرية ضمن الملفات المراد رفعها.

## نشر التعديل على Contabo

بعد ربط الخادم بالمستودع مرة واحدة، نفذ:

```bash
sudo bash /var/www/itcenterstore/scripts/deploy_server.sh
```

قبل كل نشر ينشئ السكربت نسخة احتياطية من PostgreSQL داخل:

```text
/var/backups/itcenterstore/
```

ثم يسحب آخر `main`، يثبت المتطلبات، يشغل migrations وcollectstatic، يعيد تشغيل
Gunicorn، ويفحص Nginx والموقع. يحتفظ بآخر عشر نسخ من قاعدة البيانات.

## ربط Contabo أول مرة

سننفذ هذه الخطوة مرة واحدة بعد جعل المستودع خاصًا ورفع النسخة المحلية الحالية.
سنضيف للخادم مفتاح Deploy Key للقراءة فقط، ثم نحول
`/var/www/itcenterstore` إلى نسخة Git مع إبقاء `venv` و`media` وملف البيئة
وقاعدة PostgreSQL خارج Git.
