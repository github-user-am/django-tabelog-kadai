# Generated by Django 5.0.3 on 2024-03-23 09:19

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nagoyameshi', '0004_favorite'),
    ]

    operations = [
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField(choices=[(1.0, '1'), (2.0, '2'), (3.0, '3'), (4.0, '4'), (5.0, '5')], verbose_name='score')),
                ('review_title', models.CharField(max_length=100, verbose_name='review title')),
                ('review_comment', models.TextField(verbose_name='review comment')),
                ('create_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='create at')),
                ('update_at', models.DateTimeField(auto_now=True, verbose_name='last update')),
                ('restaurant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nagoyameshi.restaurant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
