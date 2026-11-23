from django.db import migrations, models


def iniciar_entregas_pedidos_pagos(apps, schema_editor):
    Pedido = apps.get_model('core', 'Pedido')
    Pedido.objects.filter(status='PAGO').update(
        status_entrega='AGUARDANDO_PREPARACAO'
    )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_user_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='endereco_entrega',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='pedido',
            name='endereco_entrega',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='pedido',
            name='status_entrega',
            field=models.CharField(
                choices=[
                    ('NAO_INICIADA', 'Não iniciada'),
                    ('AGUARDANDO_PREPARACAO', 'Aguardando preparação'),
                    ('ENVIADO', 'Enviado'),
                    ('EM_TRANSITO', 'Em trânsito'),
                    ('SAIU_PARA_ENTREGA', 'Saiu para entrega'),
                    ('ENTREGUE', 'Entregue'),
                ],
                default='NAO_INICIADA',
                max_length=30,
            ),
        ),
        migrations.RunPython(
            iniciar_entregas_pedidos_pagos,
            migrations.RunPython.noop,
        ),
    ]
