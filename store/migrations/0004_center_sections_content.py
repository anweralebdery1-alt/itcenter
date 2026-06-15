from django.db import migrations, models
import django.db.models.deletion


def seed_center_settings(apps, schema_editor):
    SiteSettings = apps.get_model('store', 'SiteSettings')
    SiteSection = apps.get_model('store', 'SiteSection')
    settings, _ = SiteSettings.objects.get_or_create(pk=1)
    settings.site_name = 'مركز آي تي للتطوير والتدريب'
    settings.tagline = 'إلكترونيات، دورات تدريبية، وفيديوهات تعليمية في مكان واحد'
    settings.hero_title = 'مركز آي تي للتطوير والتدريب'
    settings.hero_subtitle = 'تسوق المواد الإلكترونية، سجل في الدورات، وشاهد فيديوهات تعليمية مع ملفات قابلة للتحميل.'
    settings.save()

    defaults = [
        ('قسم الإلكترونيات', 'electronics', 'كل المواد الإلكترونية المتوفرة في المخزن', '/'),
        ('الدورات التدريبية', 'courses', 'دورات عملية يمكن التسجيل فيها من الموقع', '/courses/'),
        ('فيديوهات تعليمية', 'videos', 'شروحات وملفات كود قابلة للتحميل مجاناً', '/videos/'),
        ('حول المركز', 'about', 'تعرف على المركز وفريق العمل وطرق التواصل', '/about/'),
    ]
    for order, (title, section_type, description, url) in enumerate(defaults):
        SiteSection.objects.get_or_create(
            section_type=section_type,
            defaults={'title': title, 'description': description, 'url': url, 'order': order},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_cart_order_customer_otp'),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=250)),
                ('description', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='courses/')),
                ('price', models.FloatField(default=0)),
                ('duration', models.CharField(blank=True, max_length=100)),
                ('trainer', models.CharField(blank=True, max_length=200)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='EducationalVideo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=250)),
                ('description', models.TextField(blank=True)),
                ('video_url', models.URLField(blank=True)),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='videos/')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='SiteSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('section_type', models.CharField(choices=[('electronics', 'قسم الإلكترونيات'), ('courses', 'الدورات التدريبية'), ('videos', 'فيديوهات تعليمية'), ('about', 'حول المركز'), ('custom', 'بطاقة مخصصة')], default='custom', max_length=30)),
                ('description', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='sections/')),
                ('url', models.CharField(blank=True, max_length=300)),
                ('order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['order', 'id']},
        ),
        migrations.CreateModel(
            name='TeamMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('role', models.CharField(blank=True, max_length=200)),
                ('bio', models.TextField(blank=True)),
                ('phone', models.CharField(blank=True, max_length=50)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('facebook', models.URLField(blank=True)),
                ('instagram', models.URLField(blank=True)),
                ('linkedin', models.URLField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='team/')),
                ('order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['order', 'id']},
        ),
        migrations.CreateModel(
            name='DownloadableFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=250)),
                ('description', models.TextField(blank=True)),
                ('file', models.FileField(upload_to='downloads/')),
                ('is_free', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='files', to='store.course')),
                ('video', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='files', to='store.educationalvideo')),
            ],
        ),
        migrations.RunPython(seed_center_settings, migrations.RunPython.noop),
    ]
