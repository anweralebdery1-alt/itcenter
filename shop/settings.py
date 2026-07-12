import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

# تحميل ملف .env المحلي للتطوير فقط (لا يُرفع إلى GitHub).
# على الخادم لا يوجد .env، فتُستخدم متغيّرات النظام (override=False لا يدهسها).
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=False)
except Exception:
    pass


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY")
if DEBUG and not SECRET_KEY:
    SECRET_KEY = "dev-only-change-me"
if not SECRET_KEY or (not DEBUG and SECRET_KEY == "dev-only-change-me"):
    raise ImproperlyConfigured("Set a strong SECRET_KEY environment variable before production deploy.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
if not CSRF_TRUSTED_ORIGINS:
    for host in ALLOWED_HOSTS:
        if host in ("*", "127.0.0.1", "localhost"):
            continue
        CSRF_TRUSTED_ORIGINS.append(f"https://*{host}" if host.startswith(".") else f"https://{host}")
if DEBUG:
    CSRF_TRUSTED_ORIGINS += ["http://127.0.0.1:8000", "http://localhost:8000"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "rest_framework",
    "store",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "shop.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "shop.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}
if os.environ.get("DATABASE_URL"):
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ar"
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Baghdad")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
_static_dir = BASE_DIR / "static"
STATICFILES_DIRS = [_static_dir] if _static_dir.is_dir() else []
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
SERVE_MEDIA_WITH_DJANGO = env_bool("SERVE_MEDIA_WITH_DJANGO", DEBUG)

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

SYNC_API_TOKEN = os.environ.get("SYNC_API_TOKEN")
if DEBUG and not SYNC_API_TOKEN:
    SYNC_API_TOKEN = "dev-sync-token"
if not SYNC_API_TOKEN or (not DEBUG and SYNC_API_TOKEN in {"changeme_token", "dev-sync-token"}):
    raise ImproperlyConfigured("Set a strong SYNC_API_TOKEN environment variable before production deploy.")

OTPIQ_API_URL = os.environ.get("OTPIQ_API_URL", "https://api.otpiq.com/api/sms")
OTPIQ_API_KEY = os.environ.get("OTPIQ_API_KEY", "")
OTPIQ_PROVIDER = os.environ.get("OTPIQ_PROVIDER", "whatsapp-sms")
OTPIQ_SENDER_ID = os.environ.get("OTPIQ_SENDER_ID", "")
OTPIQ_TIMEOUT = int(os.environ.get("OTPIQ_TIMEOUT", "15"))
OTPIQ_ANTI_FRAUD = env_bool("OTPIQ_ANTI_FRAUD", True)

SHOW_OTP = env_bool("SHOW_OTP", DEBUG and not OTPIQ_API_KEY)
if not DEBUG and SHOW_OTP:
    raise ImproperlyConfigured("SHOW_OTP must be False in production.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", not DEBUG)

# ---- إشعارات الويب للأدمن (Web Push / VAPID) ----
# ولّد المفتاح مرّة واحدة: python manage.py vapid_keys ثم ضع الناتج في متغيّر البيئة.
VAPID_PRIVATE_KEY_B64 = os.environ.get("VAPID_PRIVATE_KEY", "")  # base64 لملف PEM
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@itcenterstore.com")
VAPID_PRIVATE_PEM = ""
VAPID_PUBLIC_KEY = ""
if VAPID_PRIVATE_KEY_B64:
    try:
        import base64 as _b64
        from cryptography.hazmat.primitives import serialization as _ser
        VAPID_PRIVATE_PEM = _b64.b64decode(VAPID_PRIVATE_KEY_B64).decode()
        _priv = _ser.load_pem_private_key(VAPID_PRIVATE_PEM.encode(), password=None)
        _pub = _priv.public_key().public_bytes(_ser.Encoding.X962, _ser.PublicFormat.UncompressedPoint)
        VAPID_PUBLIC_KEY = _b64.urlsafe_b64encode(_pub).rstrip(b"=").decode()
    except Exception:
        VAPID_PRIVATE_PEM = ""
        VAPID_PUBLIC_KEY = ""
