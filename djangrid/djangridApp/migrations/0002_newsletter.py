# Generated by Django 4.0 on 2021-12-24 05:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangridApp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Newsletter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('subject', models.CharField(max_length=150)),
                ('contents', models.FileField(upload_to='uploaded_newsletters/')),
            ],
        ),
    ]
