from django.db import migrations, models
import django.db.models.deletion
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(User),
    ]
    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(blank=True, max_length=50, verbose_name='ชื่อ')),
                ('last_name', models.CharField(blank=True, max_length=50, verbose_name='นามสกุล')),
                ('phone_number', models.CharField(blank=True, max_length=20, verbose_name='เบอร์มือถือ')),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/', verbose_name='รูปโปรไฟล์')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=User)),
            ],
        ),
        migrations.CreateModel(
            name='EmailActivation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expired_at', models.DateTimeField()),
                ('is_used', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_activations', to=User)),
            ],
        ),
        migrations.CreateModel(
            name='OTP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='อีเมล')),
                ('code', models.CharField(max_length=6, verbose_name='รหัส OTP')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='เวลาสร้าง')),
                ('valid_until', models.DateTimeField(verbose_name='OTP หมดอายุ')),
                ('is_used', models.BooleanField(default=False, verbose_name='ถูกใช้งานแล้ว')),
            ],
        ),
        migrations.CreateModel(
            name='ExchangeRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currency', models.CharField(max_length=10)),
                ('rate', models.CharField(max_length=20)),
                ('scraped_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='InterestRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('rate', models.CharField(max_length=20)),
                ('scraped_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
