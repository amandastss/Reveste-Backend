import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('core', '0008_rename_data_pedido_pedido_criado_em_and_more')]
    operations = [
        migrations.AlterField(model_name='pedido', name='status', field=models.CharField(choices=[('PENDENTE','Pendente'),('AGUARDANDO_PAGAMENTO','Aguardando pagamento'),('PAGO','Pago'),('ENVIADO','Enviado'),('CANCELADO','Cancelado')], default='PENDENTE', max_length=30)),
        migrations.AddField(model_name='pedido', name='mercado_pago_payment_id', field=models.CharField(blank=True, max_length=255, null=True, unique=True)),
        migrations.AddField(model_name='pedido', name='mercado_pago_status', field=models.CharField(blank=True, max_length=50, null=True)),
        migrations.AddField(model_name='pedido', name='mercado_pago_status_detail', field=models.CharField(blank=True, max_length=255, null=True)),
        migrations.AddField(model_name='pedido', name='mercado_pago_idempotency_key', field=models.CharField(blank=True, max_length=36, null=True, unique=True)),
        migrations.AddField(model_name='pedido', name='pago_em', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='produto', name='disponivel', field=models.BooleanField(default=True)),
        migrations.AddField(model_name='produto', name='reserva_pedido', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='produtos_reservados', to='core.pedido')),
        migrations.AddField(model_name='produto', name='reservado_ate', field=models.DateTimeField(blank=True, null=True)),
        migrations.AlterField(model_name='itempedido', name='quantidade', field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name='itempedido', name='preco', field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name='itempedido', name='nome', field=models.CharField(blank=True, max_length=120, null=True)),
        migrations.AddField(model_name='itempedido', name='cor', field=models.CharField(blank=True, max_length=60, null=True)),
        migrations.AddField(model_name='itempedido', name='tamanho', field=models.CharField(blank=True, max_length=30, null=True)),
        migrations.AddField(model_name='itempedido', name='imagem_url', field=models.CharField(blank=True, max_length=500, null=True)),
    ]
