import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0009_checkout_pagamentos')]
    operations = [
        migrations.AddField(
            model_name='venda',
            name='vendedor',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='vendas', to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
