from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_name', models.CharField(default='متجر المكونات', max_length=200)),
                ('tagline', models.CharField(default='كل ما تحتاجه من قطع ومستلزمات إلكترونية', max_length=300)),
                ('hero_title', models.CharField(default='مكونات إلكترونية جاهزة للطلب', max_length=300)),
                ('hero_subtitle', models.TextField(default='تصفح المنتجات المتوفرة في المخزن واطلبها بنظام الدفع عند الاستلام.')),
                ('phone', models.CharField(blank=True, max_length=50)),
                ('whatsapp', models.CharField(blank=True, max_length=50)),
                ('address', models.CharField(blank=True, max_length=300)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='site/')),
                ('hero_image', models.ImageField(blank=True, null=True, upload_to='site/')),
                ('primary_color', models.CharField(default='#0B4EA2', max_length=20)),
                ('accent_color', models.CharField(default='#FF8A00', max_length=20)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'إعدادات الموقع',
                'verbose_name_plural': 'إعدادات الموقع',
            },
        ),
        migrations.AddField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='products/'),
        ),
    ]
