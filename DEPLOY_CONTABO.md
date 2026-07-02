# نشر الموقع على Contabo مع PostgreSQL

هذا الدليل يفترض أن الدومين هو `itcenterstore.com` وأن الموقع سيعمل داخليا على منفذ `8003` حتى لا يتعارض مع الموقعين الموجودين على نفس السيرفر.

## 1. DNS في Namecheap

- أضف `A Record` للدومين `itcenterstore.com` يشير إلى IP سيرفر Contabo.
- أضف `A Record` أو `CNAME` لـ `www` يشير إلى نفس السيرفر.
- انتظر انتشار DNS قبل إصدار SSL.

## 2. تثبيت المتطلبات على السيرفر

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip postgresql postgresql-contrib nginx certbot python3-certbot-nginx unzip
```

## 3. إنشاء قاعدة PostgreSQL

استبدل كلمة المرور بقيمة قوية:

```bash
sudo -u postgres psql
```

داخل PostgreSQL:

```sql
CREATE DATABASE itcenterstore_db;
CREATE USER itcenterstore_user WITH PASSWORD 'ضع_كلمة_مرور_قوية_هنا';
ALTER ROLE itcenterstore_user SET client_encoding TO 'utf8';
ALTER ROLE itcenterstore_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE itcenterstore_user SET timezone TO 'Asia/Baghdad';
GRANT ALL PRIVILEGES ON DATABASE itcenterstore_db TO itcenterstore_user;
\q
```

## 4. رفع ملفات الموقع

```bash
sudo mkdir -p /var/www/itcenterstore
sudo chown -R $USER:www-data /var/www/itcenterstore
cd /var/www/itcenterstore
```

ارفع حزمة الموقع ثم فكها:

```bash
unzip itcenterstore_deploy.zip -d /var/www/itcenterstore
```

مهم: لا نرفع `db.sqlite3` للإنتاج. قاعدة البيانات ستكون PostgreSQL عبر `DATABASE_URL`.

## 5. إعداد متغيرات البيئة

أنشئ الملف:

```bash
sudo nano /etc/itcenterstore.env
```

مثال:

```text
SECRET_KEY=replace-with-a-long-random-secret
DEBUG=False
ALLOWED_HOSTS=itcenterstore.com,www.itcenterstore.com
CSRF_TRUSTED_ORIGINS=https://itcenterstore.com,https://www.itcenterstore.com
DATABASE_URL=postgres://itcenterstore_user:ضع_كلمة_مرور_قاعدة_البيانات@127.0.0.1:5432/itcenterstore_db

SYNC_API_TOKEN=replace-with-the-same-strong-token-used-by-the-offline-app

OTPIQ_API_KEY=sk_live_replace_me
OTPIQ_PROVIDER=whatsapp-sms
OTPIQ_SENDER_ID=
OTPIQ_ANTI_FRAUD=True
SHOW_OTP=False

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SERVE_MEDIA_WITH_DJANGO=False
SECURE_HSTS_SECONDS=3600
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
TIME_ZONE=Asia/Baghdad
```

## 6. تجهيز Django

```bash
cd /var/www/itcenterstore
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
set -a
source /etc/itcenterstore.env
set +a
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
```

إذا أردت نقل بيانات التطوير الحالية إلى PostgreSQL، استخدم ملف fixture نصدره من الجهاز المحلي ثم:

```bash
python manage.py loaddata store_data.json
```

إذا كانت المنتجات ستأتي من برنامج الأوفلاين بالمزامنة، يمكن ترك قاعدة PostgreSQL فارغة بعد `migrate` ثم عمل مزامنة من البرنامج.

## 7. systemd

```ini
[Unit]
Description=itcenterstore Django app
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/itcenterstore
EnvironmentFile=/etc/itcenterstore.env
ExecStart=/var/www/itcenterstore/venv/bin/gunicorn shop.wsgi:application --bind 127.0.0.1:8003 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

احفظه:

```bash
sudo nano /etc/systemd/system/itcenterstore.service
sudo systemctl daemon-reload
sudo systemctl enable --now itcenterstore
sudo systemctl status itcenterstore
```

## 8. Nginx

```nginx
server {
    listen 80;
    server_name itcenterstore.com www.itcenterstore.com;

    location /static/ {
        alias /var/www/itcenterstore/staticfiles/;
    }

    location /media/ {
        alias /var/www/itcenterstore/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

ثم:

```bash
sudo nano /etc/nginx/sites-available/itcenterstore
sudo ln -s /etc/nginx/sites-available/itcenterstore /etc/nginx/sites-enabled/itcenterstore
sudo nginx -t
sudo systemctl reload nginx
```

## 9. SSL

```bash
sudo certbot --nginx -d itcenterstore.com -d www.itcenterstore.com
sudo systemctl restart itcenterstore
```

## 10. اختبار

```bash
curl -I https://itcenterstore.com/
curl -I https://itcenterstore.com/static/admin/css/base.css
sudo journalctl -u itcenterstore -n 80 --no-pager
```

من برنامج الأوفلاين:

```text
server_url=https://itcenterstore.com
sync_api_token=نفس قيمة SYNC_API_TOKEN
```
