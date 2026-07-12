import base64

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'يولّد مفاتيح VAPID لإشعارات الويب. انسخ السطر وضعه في متغيّر البيئة.'

    def handle(self, *args, **options):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        priv = ec.generate_private_key(ec.SECP256R1())
        pem = priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()
        pub = priv.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        appkey = base64.urlsafe_b64encode(pub).rstrip(b'=').decode()
        priv_b64 = base64.b64encode(pem.encode()).decode()

        self.stdout.write(self.style.SUCCESS('تم توليد مفاتيح VAPID. ضع السطر التالي في متغيّرات بيئة الخادم:'))
        self.stdout.write('')
        self.stdout.write('VAPID_PRIVATE_KEY=' + priv_b64)
        self.stdout.write('')
        self.stdout.write('(المفتاح العام يُشتقّ تلقائياً؛ للاطلاع فقط: ' + appkey + ')')
