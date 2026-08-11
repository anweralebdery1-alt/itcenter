import secrets
import sys

from django.core.management.base import BaseCommand

from store.models import PosDevice

# نافذة أوامر ويندوز بترميزها الافتراضي تُسقط الأمر عند طباعة العربية
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


class Command(BaseCommand):
    help = 'إدارة أجهزة نقاط البيع المصرّح لها بالمزامنة (إنشاء / عرض / إيقاف).'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['add', 'list', 'disable', 'enable', 'rotate'],
                            help='add=إضافة جهاز · list=عرض · disable/enable=إيقاف وتفعيل · rotate=تبديل الرمز')
        parser.add_argument('--name', default='', help='اسم الجهاز، مثل: حاسبة أنور')
        parser.add_argument('--device-id', default='', help='معرّف الجهاز (من settings.cfg في البرنامج)')

    def handle(self, *args, **options):
        action = options['action']

        if action == 'list':
            devices = PosDevice.objects.order_by('name')
            if not devices:
                self.stdout.write('لا توجد أجهزة مسجّلة بعد. أضف واحداً بـ: pos_device add --name "حاسبة أنور"')
                return
            for device in devices:
                state = 'مفعّل' if device.is_active else 'موقوف'
                seen = device.last_seen.strftime('%Y-%m-%d %H:%M') if device.last_seen else 'لم يتصل بعد'
                self.stdout.write(f'{device.name} · {state} · آخر اتصال: {seen}')
                self.stdout.write(f'   device_id: {device.device_id}')
            return

        if action == 'add':
            name = options['name'].strip()
            if not name:
                self.stderr.write('يجب تمرير --name')
                return
            device_id = options['device_id'].strip() or secrets.token_hex(16)
            token = secrets.token_hex(32)
            device, created = PosDevice.objects.get_or_create(
                device_id=device_id,
                defaults={'name': name, 'token': token},
            )
            if not created:
                self.stderr.write(f'الجهاز موجود مسبقاً: {device.name}')
                return
            self.stdout.write(self.style.SUCCESS(f'تم إنشاء الجهاز: {device.name}'))
            self.stdout.write('')
            self.stdout.write('ضع هذين السطرين في settings.cfg على تلك الحاسبة:')
            self.stdout.write('')
            self.stdout.write(f'device_id={device.device_id}')
            self.stdout.write(f'sync_token={device.token}')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('الرمز يظهر مرة واحدة فقط — انسخه الآن.'))
            return

        device = PosDevice.objects.filter(device_id=options['device_id'].strip()).first()
        if not device:
            self.stderr.write('لم أجد جهازاً بهذا المعرّف. اعرض الأجهزة بـ: pos_device list')
            return

        if action in ('disable', 'enable'):
            device.is_active = action == 'enable'
            device.save(update_fields=['is_active'])
            self.stdout.write(self.style.SUCCESS(
                f'{device.name}: {"مفعّل" if device.is_active else "موقوف"}'))
            return

        if action == 'rotate':
            device.token = secrets.token_hex(32)
            device.save(update_fields=['token'])
            self.stdout.write(self.style.SUCCESS(f'رمز جديد لـ {device.name}:'))
            self.stdout.write(f'sync_token={device.token}')
