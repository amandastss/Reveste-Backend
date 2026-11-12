import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class PaymentAttempt(models.Model):
    class Status(models.TextChoices):
        CREATED = 'CREATED', 'Criada'
        PROCESSING = 'PROCESSING', 'Em processamento'
        PENDING = 'PENDING', 'Pendente'
        APPROVED = 'APPROVED', 'Aprovada'
        REJECTED = 'REJECTED', 'Recusada'
        CANCELLED = 'CANCELLED', 'Cancelada'
        REFUNDED = 'REFUNDED', 'Estornada'
        RECONCILIATION_REQUIRED = 'RECONCILIATION_REQUIRED', 'Requer conciliação'
        ERROR = 'ERROR', 'Erro/resultado inconclusivo'

    class RefundStatus(models.TextChoices):
        NOT_REVIEWED = 'NOT_REVIEWED', 'Não revisado'
        REVIEW_REQUIRED = 'REVIEW_REQUIRED', 'Revisão manual necessária'
        REQUESTED = 'REQUESTED', 'Estorno solicitado manualmente'
        REFUNDED = 'REFUNDED', 'Estorno conciliado'
        FAILED = 'FAILED', 'Estorno não concluído'

    pedido = models.ForeignKey('core.Pedido', on_delete=models.PROTECT, related_name='tentativas_pagamento')
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    external_reference = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='BRL')
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CREATED)
    status_detail = models.CharField(max_length=255, blank=True)
    request_fingerprint = models.CharField(max_length=64, blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    reconciliation_note = models.TextField(blank=True)
    refund_status = models.CharField(max_length=20, choices=RefundStatus.choices, default=RefundStatus.NOT_REVIEWED)
    refund_id = models.CharField(max_length=100, blank=True)
    refund_recorded_at = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criado_em', '-pk']
        indexes = [models.Index(fields=['pedido', 'status'])]
        constraints = [
            models.CheckConstraint(
                condition=(~Q(refund_status='REFUNDED') | (Q(refund_id__gt='') & Q(refund_recorded_at__isnull=False))),
                name='estorno_conciliado_exige_evidencia',
            ),
        ]

    def clean(self):
        super().clean()
        if self.refund_status == self.RefundStatus.REFUNDED and (not self.refund_id or not self.refund_recorded_at):
            raise ValidationError('Para conciliar um estorno informe a referência externa e a data comprovada.')

    def __str__(self):
        return f'Tentativa {self.pk} do pedido {self.pedido_id}: {self.status}'


class ProductReservation(models.Model):
    class Status(models.TextChoices):
        HELD = 'HELD', 'Reservada'
        RELEASED = 'RELEASED', 'Liberada'
        CONSUMED = 'CONSUMED', 'Vendida'
        CONFLICT = 'CONFLICT', 'Conflito de pagamento'

    produto = models.ForeignKey('core.Produto', on_delete=models.PROTECT, related_name='reservas_pagamento')
    pedido = models.ForeignKey('core.Pedido', on_delete=models.PROTECT, related_name='reservas_pagamento')
    tentativa = models.ForeignKey(
        PaymentAttempt,
        on_delete=models.PROTECT,
        related_name='reservas',
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.HELD)
    criado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()
    liberado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['produto'],
                condition=Q(status__in=['HELD', 'CONFLICT']),
                name='uma_reserva_ativa_por_produto',
            ),
        ]
        indexes = [models.Index(fields=['status', 'expira_em'])]

    def __str__(self):
        return f'Reserva do produto {self.produto_id} para o pedido {self.pedido_id}'


class SellerPayout(models.Model):
    class Status(models.TextChoices):
        CONFIGURATION_REQUIRED = 'CONFIGURATION_REQUIRED', 'Aguardando configuração comercial'
        PENDING = 'PENDING', 'Devido ao vendedor'
        PAID = 'PAID', 'Pago'
        RECONCILED = 'RECONCILED', 'Conciliado'
        REFUND_REVIEW = 'REFUND_REVIEW', 'Revisão de estorno/divergência'

    pedido = models.OneToOneField('core.Pedido', on_delete=models.PROTECT, related_name='repasse')
    venda = models.OneToOneField('core.Venda', on_delete=models.PROTECT, related_name='repasse')
    vendedor = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='repasses')
    valor_bruto = models.DecimalField(max_digits=12, decimal_places=2)
    comissao = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valor_liquido = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CONFIGURATION_REQUIRED)
    referencia_externa = models.CharField(max_length=255, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    pago_em = models.DateTimeField(null=True, blank=True)
    conciliado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        Q(comissao__isnull=True, valor_liquido__isnull=True)
                        & Q(status__in=['CONFIGURATION_REQUIRED', 'REFUND_REVIEW'])
                    )
                    | (Q(comissao__isnull=False, valor_liquido__isnull=False))
                ),
                name='repasse_comissao_liquido_coerentes',
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(status__in=['PAID', 'RECONCILED']) | (Q(referencia_externa__gt='') & Q(pago_em__isnull=False))
                ),
                name='repasse_pago_exige_evidencia',
            ),
        ]

    def clean(self):
        super().clean()
        if (self.comissao is None) != (self.valor_liquido is None):
            raise ValidationError('Comissão e valor líquido devem ser definidos em conjunto.')
        if self.comissao is not None and self.valor_liquido is not None:
            if (self.comissao + self.valor_liquido).quantize(Decimal('0.01')) != self.valor_bruto:
                raise ValidationError('Comissão mais valor líquido deve corresponder ao valor bruto.')
        if self.status in {self.Status.PENDING, self.Status.PAID, self.Status.RECONCILED} and (
            self.comissao is None or self.valor_liquido is None
        ):
            raise ValidationError('Defina comissão e valor líquido conforme as regras comerciais antes do repasse.')
        if self.status in {self.Status.PAID, self.Status.RECONCILED} and (
            not self.referencia_externa or not self.pago_em
        ):
            raise ValidationError('Para marcar um repasse como pago informe a referência externa e a data comprovada.')

    def __str__(self):
        return f'Repasse do pedido {self.pedido_id}: {self.status}'
