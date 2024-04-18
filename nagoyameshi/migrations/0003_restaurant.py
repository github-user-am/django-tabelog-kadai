# Generated by Django 5.0.3 on 2024-03-23 09:04

import datetime
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nagoyameshi', '0002_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='Restaurant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('restaurant_name', models.CharField(max_length=150, verbose_name='restaurant name')),
                ('restaurant_image', models.ImageField(blank=True, default='noImage.png', upload_to='', verbose_name='restaurant image')),
                ('description', models.TextField(blank=True, null=True, verbose_name='description')),
                ('postal_code', models.CharField(max_length=30, verbose_name='postal code')),
                ('address', models.CharField(max_length=200, verbose_name='address')),
                ('opening', models.TimeField(default=datetime.time(0, 0), verbose_name='opening')),
                ('closing', models.TimeField(default=datetime.time(0, 0), verbose_name='closing')),
                ('regular_holiday', models.CharField(choices=[('sunday', '日'), ('monday', '月'), ('tuesday', '火'), ('wednesday', '水'), ('thursday', '木'), ('friday', '金'), ('saturday', '土'), ('none_holiday', '定休日なし')], max_length=20, verbose_name='regular holiday')),
                ('seat_number', models.PositiveSmallIntegerField(default=1, verbose_name='seat number')),
                ('phone_number', models.CharField(max_length=20, verbose_name='phone number')),
                ('create_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='create at')),
                ('update_at', models.DateTimeField(auto_now=True, verbose_name='last update')),
                ('restaurant_admin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('restaurant_category', models.ManyToManyField(blank=True, related_name='restaurant_categories', to='nagoyameshi.category')),
            ],
            options={
                'verbose_name': 'restaurant',
                'verbose_name_plural': 'restaurants',
            },
        ),
    ]
