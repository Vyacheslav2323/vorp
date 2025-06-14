# Generated by Django 5.2.1 on 2025-05-31 04:55

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WordClassificationRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('rule_type', models.CharField(choices=[('frequency', 'Word Frequency'), ('length', 'Word Length'), ('pattern', 'Word Pattern'), ('pos', 'Part of Speech')], max_length=20)),
                ('criteria', models.JSONField()),
                ('target_status', models.CharField(choices=[('unknown', 'Unknown'), ('learning', 'Learning'), ('learned', 'Learned')], max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='LearningMetrics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('words_learned', models.IntegerField(default=0)),
                ('words_reviewed', models.IntegerField(default=0)),
                ('time_spent_minutes', models.IntegerField(default=0)),
                ('accuracy_percentage', models.FloatField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'date')},
            },
        ),
        migrations.CreateModel(
            name='WordClassificationHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('word', models.CharField(max_length=200)),
                ('old_status', models.CharField(max_length=20)),
                ('new_status', models.CharField(max_length=20)),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('changed_by_rule', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='classification.wordclassificationrule')),
            ],
            options={
                'indexes': [models.Index(fields=['user', 'word'], name='classificat_user_id_59677f_idx'), models.Index(fields=['changed_at'], name='classificat_changed_76bad2_idx')],
            },
        ),
    ]
