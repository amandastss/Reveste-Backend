# Generated for the ReVeste Payment Brick reservation flow.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0015_pedido_mercado_pago_payment_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='reserva_pedido',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='produtos_reservados',
                to='core.pedido',
            ),
        ),
        migrations.AddField(
            model_name='produto',
            name='reservado_ate',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
