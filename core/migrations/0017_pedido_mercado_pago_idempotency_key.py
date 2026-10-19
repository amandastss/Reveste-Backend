# Generated for stable Mercado Pago payment idempotency per order.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0016_produto_reserva_pedido_reservado_ate'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='mercado_pago_idempotency_key',
            field=models.CharField(blank=True, max_length=36, null=True, unique=True),
        ),
    ]
