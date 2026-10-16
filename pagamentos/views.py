from decimal import Decimal, InvalidOperation

import mercadopago
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import ItemPedido, Pedido, Produto

from .services import confirmar_pagamento


class CriarCheckoutView(APIView):
    """Prepara um pedido para o Payment Brick sem criar preferência Checkout Pro."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        pedido = (
            Pedido.objects.select_for_update()
            .filter(usuario=request.user, status__in=['PENDENTE', 'AGUARDANDO_PAGAMENTO'])
            .order_by('id')
            .first()
        )
        if pedido is None:
            return Response(
                {'detail': 'Nenhum pedido disponível para pagamento foi encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        itens = list(pedido.itens.select_related('produto__user').all())
        if not itens:
            return Response({'detail': 'O pedido não possui itens.'}, status=status.HTTP_400_BAD_REQUEST)

        vendedores = set()
        total = Decimal('0.00')
        produtos_vistos = set()

        for item in itens:
            produto = Produto.objects.select_for_update().filter(pk=item.produto_id).first()
            if produto is None or not produto.disponivel:
                nome = item.nome or 'Peça'
                return Response(
                    {'detail': f'A peça "{nome}" não está mais disponível.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if produto.user_id == request.user.id:
                return Response(
                    {'detail': 'Você não pode comprar sua própria peça.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if item.quantidade != 1:
                return Response(
                    {'detail': 'Cada peça do brechó possui apenas uma unidade disponível.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if produto.id in produtos_vistos:
                return Response(
                    {'detail': 'O pedido contém uma peça duplicada.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            produtos_vistos.add(produto.id)
            vendedores.add(produto.user_id)
            # Usa o preço atual do banco, nunca um total enviado pelo navegador.
            item.preco = produto.preco
            item.nome = produto.nome
            item.save(update_fields=['preco', 'nome'])
            total += produto.preco

        if len(vendedores) != 1:
            return Response(
                {'detail': 'Todos os itens do pedido devem pertencer ao mesmo vendedor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if total <= Decimal('0.00'):
            return Response({'detail': 'O total do pedido precisa ser maior que zero.'}, status=status.HTTP_400_BAD_REQUEST)

        pedido.status = 'AGUARDANDO_PAGAMENTO'
        pedido.save(update_fields=['status', 'atualizado_em'])

        return Response(
            {
                'pedido_id': pedido.id,
                'status': pedido.status,
                'amount': float(total),
                'payer_email': request.user.email,
            },
            status=status.HTTP_200_OK,
        )


class ProcessarPagamentoView(APIView):
    """Recebe o token do Payment Brick e cria o pagamento usando o token privado."""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _criar_pagamento_mp(payload):
        token = getattr(settings, 'MERCADO_PAGO_ACCESS_TOKEN', None)
        if not token:
            return None, {'detail': 'Token privado do Mercado Pago não configurado.'}, status.HTTP_502_BAD_GATEWAY

        try:
            resposta = mercadopago.SDK(token).payment().create(payload)
        except Exception:
            return (
                None,
                {'detail': 'Não foi possível comunicar com o Mercado Pago. Consulte o pedido antes de tentar novamente.'},
                status.HTTP_502_BAD_GATEWAY,
            )

        dados = resposta.get('response') if isinstance(resposta, dict) else None
        if not isinstance(dados, dict) or not dados.get('id') or not dados.get('status'):
            return (
                None,
                {'detail': 'O Mercado Pago retornou uma resposta inválida.'},
                status.HTTP_502_BAD_GATEWAY,
            )
        return dados, None, None

    @staticmethod
    def _payload_pagamento(request, pedido, total):
        token = request.data.get('token')
        payment_method_id = request.data.get('payment_method_id')
        try:
            installments = int(request.data.get('installments', 1))
        except (TypeError, ValueError):
            installments = 0

        if not isinstance(token, str) or not token.strip():
            return None, 'Token de pagamento obrigatório.'
        if not isinstance(payment_method_id, str) or not payment_method_id.strip():
            return None, 'Método de pagamento obrigatório.'
        if installments < 1:
            return None, 'Quantidade de parcelas inválida.'

        payer = {'email': request.user.email}
        payer_data = request.data.get('payer') or {}
        identification = payer_data.get('identification') or {}
        if identification.get('type') and identification.get('number'):
            payer['identification'] = {
                'type': identification['type'],
                'number': identification['number'],
            }

        payload = {
            'transaction_amount': float(total),
            'token': token,
            'description': f'Compra Reveste - Pedido #{pedido.id}',
            'installments': installments,
            'payment_method_id': payment_method_id,
            'external_reference': str(pedido.id),
            'payer': payer,
        }
        notification_url = getattr(settings, 'MERCADO_PAGO_WEBHOOK_URL', None)
        if notification_url:
            payload['notification_url'] = notification_url
        issuer_id = request.data.get('issuer_id')
        if issuer_id:
            payload['issuer_id'] = issuer_id
        return payload, None

    @staticmethod
    def _resposta_pagamento(dados, pedido):
        mp_status = dados.get('status')
        payment_id = dados.get('id')

        # Nenhum estado pode ser associado a um pedido diferente.
        if str(dados.get('external_reference')) != str(pedido.id):
            return Response(
                {'detail': 'O pagamento retornado não corresponde ao pedido.'},
                status=status.HTTP_409_CONFLICT,
            )

        if mp_status == 'approved':
            try:
                valor_gateway = Decimal(str(dados.get('transaction_amount'))).quantize(Decimal('0.01'))
                valor_pedido = sum(
                    (Decimal(str(item.preco)) * item.quantidade for item in pedido.itens.all()),
                    Decimal('0.00'),
                ).quantize(Decimal('0.01'))
            except (InvalidOperation, TypeError, ValueError):
                return Response(
                    {'detail': 'Não foi possível validar o valor confirmado pelo gateway.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if valor_gateway != valor_pedido or dados.get('currency_id') != 'BRL':
                return Response(
                    {'detail': 'O valor ou a moeda do pagamento não corresponde ao pedido.'},
                    status=status.HTTP_409_CONFLICT,
                )
            try:
                confirmar_pagamento(
                    pedido_id=pedido.id,
                    payment_id=payment_id,
                    payment_status=mp_status,
                    status_detail=dados.get('status_detail'),
                    transaction_amount=valor_gateway,
                    currency_id=dados.get('currency_id'),
                )
            except ValueError as error:
                return Response({'detail': str(error)}, status=status.HTTP_409_CONFLICT)
        elif mp_status in {'pending', 'in_process'}:
            pedido.mercado_pago_payment_id = str(payment_id)
            pedido.mercado_pago_status = mp_status
            pedido.mercado_pago_status_detail = dados.get('status_detail')
            pedido.save(update_fields=[
                'mercado_pago_payment_id', 'mercado_pago_status',
                'mercado_pago_status_detail', 'atualizado_em',
            ])
        elif mp_status in {'rejected', 'cancelled'}:
            pedido.mercado_pago_payment_id = str(payment_id)
            pedido.mercado_pago_status = mp_status
            pedido.mercado_pago_status_detail = dados.get('status_detail')
            pedido.status = 'CANCELADO'
            pedido.save(update_fields=[
                'status', 'mercado_pago_payment_id', 'mercado_pago_status',
                'mercado_pago_status_detail', 'atualizado_em',
            ])
        else:
            return Response(
                {'detail': 'O Mercado Pago retornou um estado de pagamento que exige verificação.'},
                status=status.HTTP_409_CONFLICT,
            )

        return Response({
            'id': payment_id,
            'status': mp_status,
            'status_detail': dados.get('status_detail'),
            'pedido_id': pedido.id,
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        pedido_id = request.data.get('pedido_id')
        if not pedido_id:
            return Response({'detail': 'ID do pedido é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pedido_id = int(pedido_id)
        except (TypeError, ValueError):
            return Response({'detail': 'ID do pedido inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        pedido = (
            Pedido.objects.select_for_update()
            .filter(id=pedido_id, usuario=request.user)
            .first()
        )
        if pedido is None:
            return Response({'detail': 'Pedido não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if pedido.status == 'PAGO':
            return Response({'detail': 'Este pedido já foi pago.'}, status=status.HTTP_409_CONFLICT)
        if pedido.status != 'AGUARDANDO_PAGAMENTO':
            return Response(
                {'detail': 'O pedido não está preparado para receber pagamento.'},
                status=status.HTTP_409_CONFLICT,
            )
        if pedido.mercado_pago_payment_id:
            return Response(
                {'detail': 'Este pedido já possui um pagamento iniciado. Consulte o estado do pedido antes de tentar novamente.'},
                status=status.HTTP_409_CONFLICT,
            )

        itens = list(pedido.itens.select_related('produto').all())
        if not itens:
            return Response({'detail': 'O pedido não possui itens.'}, status=status.HTTP_400_BAD_REQUEST)

        total = Decimal('0.00')
        vendedores = set()
        for item in itens:
            produto = Produto.objects.select_for_update().filter(pk=item.produto_id).first()
            if produto is None or not produto.disponivel:
                return Response(
                    {'detail': 'Uma ou mais peças não estão mais disponíveis.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if produto.user_id == request.user.id or item.quantidade != 1:
                return Response(
                    {'detail': 'Os itens do pedido não são válidos para pagamento.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if Decimal(str(item.preco)) != Decimal(str(produto.preco)):
                return Response(
                    {'detail': 'O preço de uma peça mudou. Atualize o carrinho e prepare o pedido novamente.'},
                    status=status.HTTP_409_CONFLICT,
                )
            vendedores.add(produto.user_id)
            total += Decimal(str(produto.preco)) * item.quantidade

        if len(vendedores) != 1 or total <= Decimal('0.00'):
            return Response(
                {'detail': 'O pedido precisa conter itens válidos de um único vendedor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload, erro = self._payload_pagamento(request, pedido, total)
        if erro:
            return Response({'detail': erro}, status=status.HTTP_400_BAD_REQUEST)

        dados, erro, erro_status = self._criar_pagamento_mp(payload)
        if erro:
            return Response(erro, status=erro_status)

        return self._resposta_pagamento(dados, pedido)
