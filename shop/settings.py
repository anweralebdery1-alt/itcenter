import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-change-me')
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('1', 'true', 'yes', 'on')

allowed_hosts = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(',') if host.strip()]
if DEBUG and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*')

# مصادر موثوقة لإرسال النماذج (POST) عبر HTTPS على الدومين الفعلي
CSRF_TRUSTED_ORIGINS = [
    'https://' + h for h in ALLOWED_HOSTS if h not in ('*', '127.0.0.1', 'localhost')
]
INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions',
    'django.contrib.messages','django.contrib.staticfiles','django.contrib.humanize','rest_framework','store',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
ROOT_URLCONF = 'shop.urls'
TEMPLATES = [
    {'BACKEND': 'django.template.backends.django.DjangoTemplates',
     'DIRS': [os.path.join(BASE_DIR,'templates')],
     'APP_DIRS': True,
     'OPTIONS': {'context_processors':[
         'django.template.context_processors.debug','django.template.context_processors.request',
         'django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages',
     ]},
    },
]
WSGI_APPLICATION = 'shop.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3','NAME': os.path.join(BASE_DIR,'db.sqlite3'),}}
if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(os.environ['DATABASE_URL'], conn_max_age=600)
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
_static_dir = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [_static_dir] if os.path.isdir(_static_dir) else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

REST_FRAMEWORK = {'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.AllowAny']}
# Simple token for sync clients (set in production differently)
SYNC_API_TOKEN = os.environ.get('SYNC_API_TOKEN','changeme_token')

# حل مؤقت لرمز OTP (بلا بوابة SMS): يُعرض الرمز على الشاشة ويُملأ تلقائياً.
# عند تفعيل otpiq سيُرسَل عبر SMS/واتساب ولن يظهر على الشاشة.
SHOW_OTP = os.environ.get('SHOW_OTP', 'True').lower() in ('1', 'true', 'yes', 'on')

# تكامل otpiq (خدمة OTP عراقية): ضع المفتاح في متغيّر البيئة OTPIQ_API_KEY
OTPIQ_API_KEY = os.environ.get('OTPIQ_API_KEY', '')
# المزوّد: sms (رصيد SMS) | whatsapp-telegram-sms | auto ...
OTPIQ_PROVIDER = os.environ.get('OTPIQ_PROVIDER', 'sms')
