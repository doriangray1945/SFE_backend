# Generated by Django 4.2.7 on 2024-10-06 12:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cities',
            name='status',
            field=models.IntegerField(choices=[(1, 'Действует'), (2, 'Удалена')], default=1),
        ),
    ]