# Generated by Django 3.1.7 on 2022-05-10 23:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0010_source_user'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='post',
            options={},
        ),
        migrations.RemoveField(
            model_name='source',
            name='max_index',
        ),
        migrations.RemoveField(
            model_name='source',
            name='num_subs',
        ),
    ]
