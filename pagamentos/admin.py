from django.contrib import admin

from .models import PaymentAttempt, ProductReservation, SellerPayout


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'pedido', 'payment_id', 'status', 'refund_status', 'amount', 'currency', 'atualizado_em')
    list_filter = ('status', 'refund_status', 'currency')
    search_fields = ('pedido__id', 'payment_id', 'external_reference', 'refund_id')
    readonly_fields = (
        'pedido',
        'status',
        'status_detail',
        'idempotency_key',
        'payment_id',
        'external_reference',
        'amount',
        'currency',
        'response_data',
    )
    fields = (
        'pedido',
        'status',
        'status_detail',
        'idempotency_key',
        'payment_id',
        'external_reference',
        'amount',
        'currency',
        'response_data',
        'reconciliation_note',
        'refund_status',
        'refund_id',
        'refund_recorded_at',
        'criado_em',
        'atualizado_em',
    )
    readonly_fields += ('criado_em', 'atualizado_em')


@admin.register(ProductReservation)
class ProductReservationAdmin(admin.ModelAdmin):
    list_display = ('produto', 'pedido', 'tentativa', 'status', 'criado_em', 'expira_em')
    list_filter = ('status',)
    search_fields = ('produto__nome', 'pedido__id', 'tentativa__payment_id')
    readonly_fields = tuple(field.name for field in ProductReservation._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SellerPayout)
class SellerPayoutAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'vendedor', 'valor_bruto', 'valor_liquido', 'status', 'pago_em', 'conciliado_em')
    list_filter = ('status',)
    search_fields = ('pedido__id', 'vendedor__email', 'referencia_externa')
    readonly_fields = ('pedido', 'venda', 'vendedor', 'valor_bruto', 'criado_em')
    fields = (
        'pedido',
        'venda',
        'vendedor',
        'valor_bruto',
        'comissao',
        'valor_liquido',
        'status',
        'referencia_externa',
        'observacoes',
        'criado_em',
        'pago_em',
        'conciliado_em',
    )
