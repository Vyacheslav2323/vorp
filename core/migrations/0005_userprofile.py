# Generated by Django 5.2.1 on 2025-05-18 05:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_uservocabulary_unique_together_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('native_language', models.CharField(choices=[('en', 'English'), ('ko', 'Korean'), ('zh', 'Chinese'), ('ru', 'Russian')], default='en', max_length=10)),
                ('target_language', models.CharField(choices=[('en', 'English'), ('ko', 'Korean'), ('zh', 'Chinese'), ('ru', 'Russian')], default='ko', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Profile',
                'verbose_name_plural': 'User Profiles',
            },
        ),
    ]
