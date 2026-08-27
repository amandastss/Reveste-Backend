from django.db import transaction

from core.models import Pedido, Produto, Venda


@transaction.atomic
def confirmar_pagamento(pedido_id):

    pedido = (
        Pedido.objects
        .select_for_update()
        .prefetch_related(
            'itens__produto'
        )
        .get(id=pedido_id)
    )

    # Proteção contra webhook repetido
    if pedido.status == 'PAGO':
        return pedido

    itens = list(pedido.itens.all())

    if not itens:
        raise ValueError(
            'Pedido sem itens.'
        )

    vendedores = set()

    for item in itens:

        produto = (
            Produto.objects
            .select_for_update()
            .get(id=item.produto_id)
        )

        if not produto.disponivel:
            raise ValueError(
                f'Produto {produto.id} '
                'não está disponível.'
            )

        vendedores.add(produto.user)

    if len(vendedores) != 1:
        raise ValueError(
            'O pedido possui mais de um vendedor.'
        )

    vendedor = vendedores.pop()

    for item in itens:

        produto = (
            Produto.objects
            .select_for_update()
            .get(id=item.produto_id)
        )

        produto.disponivel = False

        produto.save(
            update_fields=['disponivel']
        )

    pedido.status = 'PAGO'

    pedido.save(
        update_fields=['status']
    )

    Venda.objects.get_or_create(
        pedido=pedido,
        defaults={
            'vendedor': vendedor
        }
    )

    return pedido