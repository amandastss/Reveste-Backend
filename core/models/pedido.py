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
        related_name='pedidos'
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='PENDENTE'
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    atualizado_em = models.DateTimeField(
        auto_now=True
    )

    # Identificador da preferência criada no Mercado Pago.
    # Mantido caso seja utilizado pelo fluxo do checkout.
    mercado_pago_preference_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )

    # Identificador do pagamento efetivamente criado
    # no Mercado Pago.
    mercado_pago_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )

    # Último status informado pelo Mercado Pago.
    #
    # Exemplos:
    # approved
    # pending
    # in_process
    # rejected
    # cancelled
    mercado_pago_status = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    # Detalhamento do status retornado pelo Mercado Pago.
    mercado_pago_status_detail = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    # Data e hora em que o pagamento foi confirmado
    # como aprovado.
    pago_em = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f'Pedido #{self.id} - {self.status}'
