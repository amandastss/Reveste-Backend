from decimal import Decimal
from uuid import uuid4

import mercadopago

from django.conf import settings
from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Pedido

from .services import confirmar_pagamento


class CriarCheckoutView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        pedido = (
            Pedido.objects
            .select_for_update()
            .filter(
                usuario=request.user,
                status='PENDENTE'
            )
            .prefetch_related('itens__produto')
            .first()
        )

        if not pedido:
            return Response(
                {
                    'detail':
                    'Nenhum pedido pendente foi encontrado.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        itens = list(pedido.itens.all())

        if not itens:
            return Response(
                {
                    'detail':
                    'O carrinho está vazio.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        preference_items = []
        total = Decimal('0.00')

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

            if produto.user == request.user:
                return Response(
                    {
                        'detail':
                        'Você não pode comprar sua própria peça.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            preco = Decimal(str(produto.preco))

            total += preco

            preference_items.append({
                'id': str(produto.id),
                'title': produto.nome,
                'quantity': 1,
                'unit_price': float(preco),
                'currency_id': 'BRL',
            })

        sdk = mercadopago.SDK(
            settings.MERCADO_PAGO_ACCESS_TOKEN
        )

        preference_data = {
            'items': preference_items,
            'external_reference': str(pedido.id),
        }

        preference_response = (
            sdk.preference()
            .create(preference_data)
        )

        preference = preference_response.get(
            'response'
        )

        if not preference:
            return Response(
                {
                    'detail':
                    'Não foi possível preparar o pagamento.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        pedido.status = 'AGUARDANDO_PAGAMENTO'
        pedido.mercado_pago_preference_id = preference['id']

        pedido.save(
            update_fields=[
                'status',
                'mercado_pago_preference_id'
            ]
        )

        return Response(
            {
                'pedido_id': pedido.id,
                'preference_id': preference['id'],
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
            .prefetch_related('itens__produto')
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

        itens = list(pedido.itens.all())

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

            if produto.user == request.user:
                return Response(
                    {
                        'detail':
                        'Você não pode comprar sua própria peça.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            total_backend += Decimal(
                str(produto.preco)
            )

        form_data = request.data

        token = form_data.get('token')
        payment_method_id = form_data.get(
            'payment_method_id'
        )
        installments = form_data.get(
            'installments',
            1
        )
        payer = form_data.get('payer', {})

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

        issuer_id = form_data.get('issuer_id')

        if issuer_id:
            payment_data['issuer_id'] = issuer_id

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

        request_options = (
            mercadopago.config.RequestOptions()
        )

        request_options.custom_headers = {
            'x-idempotency-key': str(
                uuid4()
            )
        }

        payment_response = (
            sdk.payment().create(
                payment_data,
                request_options
            )
        )

        pagamento = payment_response.get(
            'response'
        )

        if not pagamento:
            return Response(
                {
                    'detail':
                    'Não foi possível processar o pagamento.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        pagamento_status = pagamento.get(
            'status'
        )

        if pagamento_status == 'approved':

            confirmar_pagamento(
                pedido.id
            )

        return Response(
            {
                'pedido_id': pedido.id,
                'payment_id': pagamento.get('id'),
                'status': pagamento_status,
                'status_detail': pagamento.get(
                    'status_detail'
                ),
            },
            status=status.HTTP_200_OK
        )