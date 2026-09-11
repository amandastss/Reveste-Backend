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


def obter_pedido_do_checkout(usuario):
    """
    Retorna o pedido atual do usuário.

    O pedido pode estar:
    - PENDENTE
    - AGUARDANDO_PAGAMENTO
    """

    return (
        Pedido.objects
        .select_for_update()
        .filter(
            usuario=usuario,
            status__in=[
                'PENDENTE',
                'AGUARDANDO_PAGAMENTO',
            ],
        )
        .prefetch_related('itens__produto')
        .order_by('id')
        .first()
    )


class CriarCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _validar_e_preparar_itens(itens, usuario):

        total = Decimal('0.00')
        preference_items = []

        for item in itens:
            produto = item.produto

            if not produto.disponivel:
                return (
                    f'A peça "{produto.nome}" não está mais disponível.',
                    None,
                    None,
                )

            if produto.user_id == usuario.id:
                return (
                    'Você não pode comprar sua própria peça.',
                    None,
                    None,
                )

            preco = Decimal(str(item.preco))

            total += preco

            preference_items.append({
                'id': str(produto.id),
                'title': item.nome or produto.nome,
                'quantity': 1,
                'unit_price': float(preco),
                'currency_id': 'BRL',
            })

        return None, total, preference_items

    @staticmethod
    def _criar_preferencia(pedido, itens):

        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

        try:
            response = sdk.preference().create({
                'items': itens,
                'external_reference': str(pedido.id),
            })
        except Exception:
            return None

        preference = response.get('response')

        if not preference:
            return None

        return preference.get('id')

    def post(self, request):

        # Primeiro localizamos o pedido e validamos o estado.
        with transaction.atomic():
            pedido = obter_pedido_do_checkout(request.user)

            if not pedido:
                return Response(
                    {'detail': ('Nenhum pedido disponível para pagamento foi encontrado.')},
                    status=status.HTTP_404_NOT_FOUND,
                )

            itens = list(pedido.itens.select_related('produto').all())

            if not itens:
                return Response(
                    {'detail': ('O pedido não possui itens.')},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            erro, total, preference_items = self._validar_e_preparar_itens(
                itens,
                request.user,
            )

            if erro:
                return Response(
                    {'detail': erro},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            preference_id = pedido.mercado_pago_preference_id

            pedido_id = pedido.id

        # A chamada ao Mercado Pago acontece fora da
        # transação do banco.
        if not preference_id:
            preference_id = self._criar_preferencia(
                pedido,
                preference_items,
            )

            if not preference_id:
                return Response(
                    {'detail': ('Não foi possível preparar o pagamento no Mercado Pago.')},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            # Salvamos a preferência somente depois
            # que o Mercado Pago retornou sucesso.
            with transaction.atomic():
                pedido = Pedido.objects.select_for_update().get(
                    id=pedido_id,
                    usuario=request.user,
                )

                if pedido.status == 'PAGO':
                    return Response(
                        {
                            'detail': ('Este pedido já foi pago.'),
                            'pedido_id': pedido.id,
                            'status': pedido.status,
                        },
                        status=status.HTTP_200_OK,
                    )

                pedido.mercado_pago_preference_id = preference_id

                pedido.status = 'AGUARDANDO_PAGAMENTO'

                pedido.save(
                    update_fields=[
                        'mercado_pago_preference_id',
                        'status',
                        'atualizado_em',
                    ]
                )

        else:
            with transaction.atomic():
                pedido = Pedido.objects.select_for_update().get(
                    id=pedido_id,
                    usuario=request.user,
                )

                if pedido.status == 'PENDENTE':
                    pedido.status = 'AGUARDANDO_PAGAMENTO'

                    pedido.save(
                        update_fields=[
                            'status',
                            'atualizado_em',
                        ]
                    )

        return Response(
            {
                'pedido_id': pedido_id,
                'preference_id': preference_id,
                'total': float(total),
            },
            status=status.HTTP_200_OK,
        )


class ProcessarPagamentoView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _validar_itens(itens, usuario):

        total = Decimal('0.00')

        for item in itens:
            produto = item.produto

            if not produto.disponivel:
                return (
                    f'A peça "{produto.nome}" não está mais disponível.',
                    None,
                )

            if produto.user_id == usuario.id:
                return (
                    'Você não pode comprar sua própria peça.',
                    None,
                )

            if item.quantidade != 1:
                return (
                    'Produtos do brechó possuem apenas uma unidade disponível.',
                    None,
                )

            total += Decimal(str(item.preco))

        return None, total

    @staticmethod
    def _criar_pagamento(
        request,
        pedido_id,
        total,
    ):

        form_data = request.data

        token = form_data.get('token')
        payment_method_id = form_data.get('payment_method_id')

        installments = form_data.get(
            'installments',
            1,
        )

        payer = form_data.get(
            'payer',
            {},
        )

        erro_validacao = None

        if not payment_method_id:
            erro_validacao = 'Método de pagamento não informado.'
        elif not payer.get('email'):
            erro_validacao = 'E-mail do comprador não informado.'

        if not erro_validacao:
            try:
                installments = int(installments or 1)
            except (TypeError, ValueError):
                erro_validacao = 'Quantidade de parcelas inválida.'

        if not erro_validacao and installments < 1:
            erro_validacao = 'Quantidade de parcelas inválida.'

        if erro_validacao:
            return (
                None,
                Response(
                    {'detail': erro_validacao},
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )

        payment_data = {
            'transaction_amount': float(total),
            'description': (f'Pedido #{pedido_id} - ReVeste'),
            'payment_method_id': payment_method_id,
            'installments': installments,
            'payer': {
                'email': payer['email'],
            },
            'external_reference': str(pedido_id),
        }

        if token:
            payment_data['token'] = token

        issuer_id = form_data.get('issuer_id')

        if issuer_id:
            payment_data['issuer_id'] = issuer_id

        identification = payer.get('identification')

        if identification and identification.get('type') and identification.get('number'):
            payment_data['payer']['identification'] = {
                'type': identification['type'],
                'number': identification['number'],
            }

        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

        # Cada tentativa de pagamento recebe uma
        # chave própria de idempotência.
        #
        # O Mercado Pago exige essa chave para
        # evitar pagamentos duplicados.
        idempotency_key = str(uuid4())

        request_options = mercadopago.config.RequestOptions()

        request_options.custom_headers = {'x-idempotency-key': idempotency_key}

        try:
            payment_response = sdk.payment().create(
                payment_data,
                request_options,
            )
        except Exception:
            return (
                None,
                Response(
                    {'detail': ('Não foi possível comunicar com o Mercado Pago.')},
                    status=status.HTTP_502_BAD_GATEWAY,
                ),
            )

        pagamento = payment_response.get('response')

        if not pagamento:
            return (
                None,
                Response(
                    {'detail': ('O Mercado Pago não retornou os dados do pagamento.')},
                    status=status.HTTP_502_BAD_GATEWAY,
                ),
            )

        return pagamento, None

    def post(self, request):

        # Primeiro buscamos o pedido e validamos
        # todos os dados dentro de uma transação curta.
        with transaction.atomic():
            pedido = (
                Pedido.objects
                .select_for_update()
                .filter(
                    usuario=request.user,
                    status='AGUARDANDO_PAGAMENTO',
                )
                .prefetch_related('itens__produto')
                .order_by('id')
                .first()
            )

            if not pedido:
                return Response(
                    {'detail': ('Nenhum pedido aguardando pagamento foi encontrado.')},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if pedido.status == 'PAGO':
                return Response(
                    {
                        'detail': ('Este pedido já foi pago.'),
                        'pedido_id': pedido.id,
                        'status': pedido.status,
                    },
                    status=status.HTTP_200_OK,
                )

            itens = list(pedido.itens.select_related('produto').all())

            if not itens:
                return Response(
                    {'detail': ('O pedido não possui itens.')},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            erro, total = self._validar_itens(
                itens,
                request.user,
            )

            if erro:
                return Response(
                    {'detail': erro},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            pedido_id = pedido.id

        # A comunicação externa com o Mercado Pago
        # acontece fora da transação do banco.
        pagamento, erro_response = self._criar_pagamento(
            request,
            pedido_id,
            total,
        )

        if erro_response:
            return erro_response

        pagamento_id = pagamento.get('id')
        pagamento_status = pagamento.get('status')
        status_detail = pagamento.get('status_detail')

        # Guardamos imediatamente no pedido o resultado
        # retornado pelo Mercado Pago.
        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().get(
                id=pedido_id,
                usuario=request.user,
            )

            pedido.mercado_pago_payment_id = str(pagamento_id) if pagamento_id else None

            pedido.mercado_pago_status = pagamento_status

            pedido.mercado_pago_status_detail = status_detail

            pedido.save(
                update_fields=[
                    'mercado_pago_payment_id',
                    'mercado_pago_status',
                    'mercado_pago_status_detail',
                    'atualizado_em',
                ]
            )

        # Apenas pagamentos aprovados podem tentar
        # concluir imediatamente o pedido.
        #
        # O webhook continuará sendo a confirmação
        # definitiva para manter o pedido sincronizado
        # com o Mercado Pago.
        if pagamento_status == 'approved':
            confirmar_pagamento(pedido_id)

        return Response(
            {
                'pedido_id': pedido_id,
                'payment_id': pagamento_id,
                'status': pagamento_status,
                'status_detail': status_detail,
            },
            status=status.HTTP_200_OK,
        )
