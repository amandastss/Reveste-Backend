from django.db import transaction
from django.utils import timezone

from core.models import Pedido, Produto, Venda


def _atualizar_pagamento_existente(
    pedido,
    payment_id,
    payment_status,
    status_detail,
):
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

    for item in itens:
        produto = Produto.objects.select_for_update().get(id=item.produto_id)

        if not produto.disponivel:
            raise ValueError(f'O produto "{produto.nome}" não está mais disponível.')

        if produto.user_id == pedido.usuario_id:
            raise ValueError('O comprador não pode comprar o próprio produto.')

        if item.quantidade != 1:
            raise ValueError('Produtos do brechó possuem apenas uma unidade disponível.')

        vendedores.add(produto.user_id)
        produtos.append(produto)

    if len(vendedores) != 1:
        raise ValueError('O pedido possui mais de um vendedor.')

    return vendedores.pop(), produtos


@transaction.atomic
def confirmar_pagamento(
    pedido_id,
    payment_id=None,
    payment_status=None,
    status_detail=None,
):
    """
    Confirma definitivamente um pedido após a aprovação
    do pagamento pelo Mercado Pago.

    Esta função é a responsável por:
    - registrar os dados do pagamento;
    - marcar os produtos como indisponíveis;
    - marcar o pedido como pago;
    - criar a venda.

    A função é protegida contra chamadas repetidas.
    """

    if payment_status is not None and payment_status != 'approved':
        raise ValueError('Somente pagamentos aprovados podem confirmar uma compra.')

    pedido = Pedido.objects.select_for_update().prefetch_related('itens__produto').get(id=pedido_id)

    # Proteção contra webhook ou confirmação repetida.
    if pedido.status == 'PAGO':
        return _atualizar_pagamento_existente(
            pedido,
            payment_id,
            payment_status,
            status_detail,
        )

    if pedido.status != 'AGUARDANDO_PAGAMENTO':
        raise ValueError('O pedido não está aguardando pagamento.')

    itens = list(pedido.itens.select_related('produto__user').all())

    if not itens:
        raise ValueError('Pedido sem itens.')

    vendedor_id, produtos = _validar_produtos_do_pedido(
        pedido,
        itens,
    )

    # Somente agora, depois da confirmação do pagamento,
    # os produtos são retirados da disponibilidade.
    for produto in produtos:
        produto.disponivel = False

        produto.save(update_fields=['disponivel'])

    pedido.status = 'PAGO'
    pedido.mercado_pago_payment_id = str(payment_id) if payment_id else pedido.mercado_pago_payment_id
    pedido.mercado_pago_status = payment_status if payment_status else pedido.mercado_pago_status
    pedido.mercado_pago_status_detail = status_detail if status_detail else pedido.mercado_pago_status_detail
    pedido.pago_em = timezone.now()

    pedido.save(
        update_fields=[
            'status',
            'mercado_pago_payment_id',
            'mercado_pago_status',
            'mercado_pago_status_detail',
            'pago_em',
            'atualizado_em',
        ]
    )

    # A venda é criada uma única vez.
    Venda.objects.get_or_create(
        pedido=pedido,
        defaults={
            'vendedor_id': vendedor_id,
        },
    )

    return pedido
