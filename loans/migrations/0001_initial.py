# Generated by Django 4.2.21 on 2025-06-25 07:53

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BankLoan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('loan_type', models.CharField(choices=[('Pre-Finance', 'Pre-Finance'), ('Working Capital', 'Working Capital'), ('Hire Purchase', 'Hire Purchase')], max_length=20)),
                ('agreement_date', models.DateField(default=django.utils.timezone.now)),
                ('principal_amount', models.DecimalField(decimal_places=2, max_digits=16)),
                ('interest_rate', models.DecimalField(decimal_places=2, max_digits=5)),
                ('outstanding_balance', models.DecimalField(decimal_places=2, max_digits=16)),
                ('status', models.CharField(choices=[('Active', 'Active'), ('Closed', 'Closed')], default='Active', max_length=20)),
            ],
        ),
    ]
