from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0035_product_reviewed'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='alibaba_url',
            field=models.URLField(
                blank=True, max_length=600, verbose_name='رابط علي بابا',
                help_text='رابط المنتج على علي بابا (خطة التسعير الثالثة — يُقارَن سعر الجملة).'),
        ),
    ]
