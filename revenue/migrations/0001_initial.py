from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal
from django.utils import timezone

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('cashflow', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='RevenueJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=timezone.now)),
                ('job_code', models.CharField(choices=[('Job1', 'Excavation and Removal of Overburden'), ('Job2', 'Extraction of Lignite'), ('Job3', 'Conveying of Overburden'), ('Job4', '\u0e04\u0e48\u0e32 k'), ('DieselSale', '\u0e23\u0e32\u0e22\u0e44\u0e14\u0e49\u0e08\u0e32\u0e01\u0e01\u0e32\u0e23\u0e02\u0e32\u0e22\u0e19\u0e49\u0e33\u0e21\u0e31\u0e19\u0e14\u0e35\u0e40\u0e0b\u0e25'), ('Other', '\u0e23\u0e32\u0e22\u0e44\u0e14\u0e49\u0e2d\u0e37\u0e48\u0e19\u0e46')], max_length=20)),
                ('description', models.CharField(blank=True, help_text="\u0e2d\u0e18\u0e34\u0e1a\u0e32\u0e22\u0e07\u0e32\u0e19\u0e2b\u0e23\u0e37\u0e2d\u0e1c\u0e25\u0e07\u0e32\u0e19 (\u0e40\u0e0a\u0e48\u0e19 'Job \u0e40\u0e14\u0e37\u0e2d\u0e19 \u0e21.\u0e04. 2568')", max_length=200)),
                ('volume', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('income_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('status', models.CharField(choices=[('Pending', 'Pending'), ('Requested_PN', 'Requested PN'), ('Invoiced', 'Invoiced'), ('Paid', 'Paid')], default='Pending', max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='AccountsReceivable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_number', models.CharField(max_length=50, unique=True)),
                ('invoice_date', models.DateField()),
                ('due_date', models.DateField()),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('paid_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('status', models.CharField(choices=[('Unpaid', 'Unpaid'), ('Partial', 'Partially Paid'), ('Paid', 'Paid')], default='Unpaid', max_length=20)),
                ('bank_account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='cashflow.bankaccount')),
                ('revenue_job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ar_records', to='revenue.revenuejob')),
            ],
        ),
    ]
