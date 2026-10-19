from django.conf import settings
from django.db import models


class Pedido(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('AGUARDANDO_PAGAMENTO', 'Aguardando pagamento'),
        ('PAGO', 'Pago'),
        ('CANCELADO', 'Cancelado'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pedidos',
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDENTE')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    # Campo legado mantido para compatibilidade com dados anteriores.
    mercado_pago_preference_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    mercado_pago_payment_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    mercado_pago_idempotency_key = models.CharField(max_length=36, null=True, blank=True, unique=True)
    mercado_pago_status = models.CharField(max_length=50, null=True, blank=True)
    mercado_pago_status_detail = models.CharField(max_length=255, null=True, blank=True)
    pago_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Pedido #{self.id} - {self.status}'
