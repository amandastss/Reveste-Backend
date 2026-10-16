from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from core.models import Pedido, Produto, Venda


def _atualizar_pagamento_existente(pedido, payment_id, payment_status, status_detail):
    if payment_id and pedido.mercado_pago_payment_id and str(payment_id) != str(pedido.mercado_pago_payment_id):
        raise ValueError('O pedido já foi confirmado com outro pagamento.')
    campos_atualizados = []
    if payment_id and not pedido.mercado_pago_payment_id:
        pedido.mercado_pago_payment_id = str(payment_id)
        campos_atualizados.append('mercado_pago_payment_id')
    if payment_status and not pedido.mercado_pago_status:
        pedido.mercado_pago_status = payment_status
        campos_atualizados.append('mercado_pago_status')
    if status_detail and not pedido.mercado_pago_status_detail:
        pedido.mercado_pago_status_detail = status_detail
        campos_atualizados.append('mercado_pago_status_detail')
    if campos_atualizados:
        campos_atualizados.append('atualizado_em')
        pedido.save(update_fields=campos_atualizados)
    return pedido


def _validar_produtos_do_pedido(pedido, itens):
    vendedores = set()
    produtos = []
    total = Decimal('0.00')
    for item in itens:
        produto = Produto.objects.select_for_update().get(id=item.produto_id)
        if not produto.disponivel:
            raise ValueError(f'O produto "{produto.nome}" não está mais disponível.')
        if produto.user_id == pedido.usuario_id:
            raise ValueError('O comprador não pode comprar o próprio produto.')
        if item.quantidade != 1:
            raise ValueError('Produtos do brechó possuem apenas uma unidade disponível.')
        if Decimal(str(item.preco)) != Decimal(str(produto.preco)):
            raise ValueError('O preço do produto mudou desde a preparação do pedido.')
        vendedores.add(produto.user_id)
        produtos.append(produto)
        total += Decimal(str(produto.preco)) * item.quantidade
    if len(vendedores) != 1:
        raise ValueError('O pedido deve conter produtos de apenas um vendedor.')
    return vendedores.pop(), produtos, total


@transaction.atomic
def confirmar_pagamento(
    pedido_id,
    payment_id=None,
    payment_status=None,
    status_detail=None,
    transaction_amount=None,
    currency_id=None,
):
    """Confirma pedido, indisponibiliza as peças e cria a venda idempotentemente."""
    if payment_status is not None and payment_status != 'approved':
        raise ValueError('Somente pagamentos aprovados podem confirmar uma compra.')
    if currency_id is not None and currency_id != 'BRL':
        raise ValueError('A moeda do pagamento não corresponde ao real brasileiro.')

    pedido = Pedido.objects.select_for_update().get(id=pedido_id)
    if pedido.status == 'PAGO':
        return _atualizar_pagamento_existente(pedido, payment_id, payment_status, status_detail)
    if pedido.status != 'AGUARDANDO_PAGAMENTO':
        raise ValueError('O pedido não está aguardando pagamento.')

    itens = list(pedido.itens.select_related('produto__user').all())
    if not itens:
        raise ValueError('Pedido sem itens.')

    vendedor_id, produtos, total_real = _validar_produtos_do_pedido(pedido, itens)
    if transaction_amount is not None:
        try:
            valor_confirmado = Decimal(str(transaction_amount)).quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError('O valor confirmado pelo gateway é inválido.') from None
        if valor_confirmado != total_real.quantize(Decimal('0.01')):
            raise ValueError('O valor confirmado pelo gateway não corresponde ao total do pedido.')

    for produto in produtos:
        produto.disponivel = False
        produto.save(update_fields=['disponivel'])

    pedido.status = 'PAGO'
    pedido.mercado_pago_payment_id = str(payment_id) if payment_id else pedido.mercado_pago_payment_id
    pedido.mercado_pago_status = payment_status if payment_status else pedido.mercado_pago_status
    pedido.mercado_pago_status_detail = status_detail if status_detail else pedido.mercado_pago_status_detail
    pedido.pago_em = timezone.now()
    pedido.save(update_fields=[
        'status', 'mercado_pago_payment_id', 'mercado_pago_status',
        'mercado_pago_status_detail', 'pago_em', 'atualizado_em',
    ])
    Venda.objects.get_or_create(pedido=pedido, defaults={'vendedor_id': vendedor_id})
    return pedido
