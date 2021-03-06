# Generated by Django 2.2.5 on 2021-05-02 07:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0006_auto_20190901_1644'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='image_url',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name='source',
            name='feed_url',
            field=models.CharField(max_length=512),
        ),
        migrations.AlterField(
            model_name='source',
            name='image_url',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name='source',
            name='last_302_url',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name='source',
            name='last_polled',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
