from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

import mercadopago

from django.conf import settings
from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Pedido

from .services import confirmar_pagamento


def obter_pedido_do_checkout(usuario):
    """
    Retorna o pedido atual do usuário.

    Primeiro procura um pedido que ainda não entrou no checkout.
    Se ele já estiver aguardando pagamento, reutiliza o mesmo pedido.
    """

    pedido = (
        Pedido.objects
        .select_for_update()
        .filter(
            usuario=usuario,
            status__in=[
                'PENDENTE',
                'AGUARDANDO_PAGAMENTO',
            ]
        )
        .prefetch_related(
            'itens__produto'
        )
        .order_by('id')
        .first()
    )

    return pedido


class CriarCheckoutView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        pedido = obter_pedido_do_checkout(
            request.user
        )

        if not pedido:
            return Response(
                {
                    'detail':
                    'Nenhum pedido disponível para pagamento foi encontrado.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        itens = list(
            pedido.itens.all()
        )

        if not itens:
            return Response(
                {
                    'detail':
                    'O pedido não possui itens.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        total = Decimal('0.00')
        preference_items = []

        for item in itens:

            produto = item.produto

            if not produto.disponivel:
                return Response(
                    {
                        'detail':
                        f'A peça "{produto.nome}" '
                        'não está mais disponível.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if produto.user_id == request.user.id:
                return Response(
                    {
                        'detail':
                        'Você não pode comprar sua própria peça.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # O preço salvo no item do pedido representa
            # o valor da peça no momento em que ela foi adicionada.
            preco = Decimal(
                str(item.preco)
            )

            total += preco

            preference_items.append(
                {
                    'id': str(produto.id),
                    'title': item.nome or produto.nome,
                    'quantity': 1,
                    'unit_price': float(preco),
                    'currency_id': 'BRL',
                }
            )

        preference_id = (
            pedido.mercado_pago_preference_id
        )

        # Se ainda não existir uma preferência,
        # cria uma e salva no pedido.
        if not preference_id:

            sdk = mercadopago.SDK(
                settings.MERCADO_PAGO_ACCESS_TOKEN
            )

            preference_response = (
                sdk.preference().create(
                    {
                        'items': preference_items,
                        'external_reference': str(
                            pedido.id
                        ),
                    }
                )
            )

            preference = (
                preference_response.get(
                    'response'
                )
            )

            if not preference:
                return Response(
                    {
                        'detail':
                        'Não foi possível preparar o pagamento.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            preference_id = preference.get(
                'id'
            )

            if not preference_id:
                return Response(
                    {
                        'detail':
                        'O Mercado Pago não retornou '
                        'uma preferência válida.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            pedido.mercado_pago_preference_id = (
                preference_id
            )

        # Se já estava aguardando pagamento,
        # continua normalmente.
        pedido.status = (
            'AGUARDANDO_PAGAMENTO'
        )

        pedido.save(
            update_fields=[
                'status',
                'mercado_pago_preference_id',
                'atualizado_em',
            ]
        )

        return Response(
            {
                'pedido_id': pedido.id,
                'preference_id': preference_id,
                'total': float(total),
            },
            status=status.HTTP_200_OK
        )


class ProcessarPagamentoView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        pedido = (
            Pedido.objects
            .select_for_update()
            .filter(
                usuario=request.user,
                status='AGUARDANDO_PAGAMENTO'
            )
            .prefetch_related(
                'itens__produto'
            )
            .order_by('id')
            .first()
        )

        if not pedido:
            return Response(
                {
                    'detail':
                    'Nenhum pedido aguardando pagamento '
                    'foi encontrado.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        itens = list(
            pedido.itens.all()
        )

        if not itens:
            return Response(
                {
                    'detail':
                    'O pedido não possui itens.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        total_backend = Decimal('0.00')

        for item in itens:

            produto = item.produto

            if not produto.disponivel:
                return Response(
                    {
                        'detail':
                        f'A peça "{produto.nome}" '
                        'não está mais disponível.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if produto.user_id == request.user.id:
                return Response(
                    {
                        'detail':
                        'Você não pode comprar sua própria peça.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            total_backend += Decimal(
                str(item.preco)
            )

        form_data = request.data

        token = form_data.get(
            'token'
        )

        payment_method_id = form_data.get(
            'payment_method_id'
        )

        installments = form_data.get(
            'installments',
            1
        )

        payer = form_data.get(
            'payer',
            {}
        )

        if not payment_method_id:
            return Response(
                {
                    'detail':
                    'Método de pagamento não informado.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not payer.get('email'):
            return Response(
                {
                    'detail':
                    'E-mail do comprador não informado.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_data = {
            'transaction_amount': float(
                total_backend
            ),
            'description': (
                f'Pedido #{pedido.id} - ReVeste'
            ),
            'payment_method_id':
                payment_method_id,
            'installments': int(
                installments or 1
            ),
            'payer': {
                'email': payer['email']
            },
            'external_reference': str(
                pedido.id
            ),
        }

        if token:
            payment_data['token'] = token

        issuer_id = form_data.get(
            'issuer_id'
        )

        if issuer_id:
            payment_data['issuer_id'] = (
                issuer_id
            )

        identification = payer.get(
            'identification'
        )

        if (
            identification
            and identification.get('type')
            and identification.get('number')
        ):
            payment_data['payer'][
                'identification'
            ] = {
                'type':
                identification['type'],
                'number':
                identification['number'],
            }

        sdk = mercadopago.SDK(
            settings.MERCADO_PAGO_ACCESS_TOKEN
        )

        # A mesma compra usa sempre a mesma chave
        # de idempotência.
        #
        # Isso evita criar cobranças duplicadas caso
        # o frontend envie a mesma solicitação novamente.
        idempotency_key = str(
            uuid5(
                NAMESPACE_URL,
                f'reveste-pedido-{pedido.id}'
            )
        )

        request_options = (
            mercadopago.config.RequestOptions()
        )

        request_options.custom_headers = {
            'x-idempotency-key':
            idempotency_key
        }

        payment_response = (
            sdk.payment().create(
                payment_data,
                request_options
            )
        )

        pagamento = (
            payment_response.get(
                'response'
            )
        )

        if not pagamento:
            return Response(
                {
                    'detail':
                    'Não foi possível processar o pagamento.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        pagamento_status = (
            pagamento.get('status')
        )

        # Cartão aprovado imediatamente
        if pagamento_status == 'approved':

            confirmar_pagamento(
                pedido.id
            )

        return Response(
            {
                'pedido_id': pedido.id,
                'payment_id': pagamento.get(
                    'id'
                ),
                'status': pagamento_status,
                'status_detail': pagamento.get(
                    'status_detail'
                ),
            },
            status=status.HTTP_200_OK
        )