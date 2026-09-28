from decimal import Decimal

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
    """Retorna o pedido atual do usuário em estado aceitável para pagamento."""
    return (
        Pedido.objects
        .select_for_update()
        .filter(
            usuario=usuario,
            status__in=['PENDENTE', 'AGUARDANDO_PAGAMENTO'],
        )
        .prefetch_related('itens__produto')
        .order_by('id')
        .first()
    )


class CriarCheckoutView(APIView):
    """Valida o pedido e chama o Mercado Pago para criar a preferência do checkout."""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _validar_e_preparar_itens(itens, usuario):
        total = Decimal('0.00')

        for item in itens:
            produto = item.produto
            if not produto.disponivel:
                return f'A peça "{produto.nome}" não está mais disponível.', None
            if produto.user_id == usuario.id:
                return 'Você não pode comprar sua própria peça.', None
            total += Decimal(str(item.preco))

        return None, total

    @staticmethod
    def _montar_payload_preferencia(pedido, usuario, total_calculado):
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        payload = {
            'items': [
                {
                    'title': f'Pedido #{pedido.id}',
                    'quantity': 1,
                    'unit_price': float(total_calculado),
                    'currency_id': 'BRL',
                }
            ],
            'payer': {'email': usuario.email},
            'external_reference': str(pedido.id),
            'notification_url': getattr(settings, 'MERCADO_PAGO_WEBHOOK_URL', None),
            'back_urls': {
                'success': f'{frontend_url}/checkout/success?pedido_id={pedido.id}&status=approved',
                'failure': f'{frontend_url}/checkout/failure?pedido_id={pedido.id}&status=rejected',
                'pending': f'{frontend_url}/checkout/pending?pedido_id={pedido.id}&status=pending',
            },
        }

        if not payload['notification_url']:
            payload.pop('notification_url')

        return payload

    def post(self, request):
        pedido = obter_pedido_do_checkout(request.user)
        if not pedido:
            return Response(
                {'detail': 'Nenhum pedido disponível para pagamento foi encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if pedido.status == 'PAGO':
            return Response(
                {'detail': 'Este pedido já foi pago.', 'pedido_id': pedido.id, 'status': pedido.status},
                status=status.HTTP_200_OK,
            )

        itens = list(pedido.itens.select_related('produto').all())
        if not itens:
            return Response(
                {'detail': 'O pedido não possui itens.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        erro, total_calculado = self._validar_e_preparar_itens(itens, request.user)
        if erro:
            return Response({'detail': erro}, status=status.HTTP_400_BAD_REQUEST)

        payload = self._montar_payload_preferencia(pedido, request.user, total_calculado)
        token = settings.MERCADO_PAGO_ACCESS_TOKEN
        if not token:
            return Response(
                {'detail': 'Token do Mercado Pago não configurado.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        sdk = mercadopago.SDK(token)
        try:
            resposta_mp = sdk.preference().create(payload)
        except Exception as exc:
            return Response(
                {'detail': f'Erro ao criar preferência do Mercado Pago: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        resposta = resposta_mp.get('response') if isinstance(resposta_mp, dict) else None
        if not resposta:
            return Response(
                {'detail': 'O Mercado Pago retornou uma resposta vazia ao criar a preferência.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        pedido.status = 'AGUARDANDO_PAGAMENTO'
        pedido.mercado_pago_preference_id = resposta.get('id')
        pedido.save(update_fields=['status', 'mercado_pago_preference_id', 'atualizado_em'])

        return Response(
            {
                'pedido_id': pedido.id,
                'amount': float(total_calculado),
                'payer_email': request.user.email,
                'preference_id': resposta.get('id'),
                'init_point': resposta.get('init_point'),
                'sandbox_init_point': resposta.get('sandbox_init_point'),
            },
            status=status.HTTP_200_OK,
        )


class ProcessarPagamentoView(APIView):
    """Recebe o token do Payment Brick e efetiva o pagamento no Mercado Pago."""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _montar_payload_pagamento(request, pedido, total_real):
        payer = {'email': request.user.email}
        identification = (request.data.get('payer') or {}).get('identification') or {}
        if identification.get('type') and identification.get('number'):
            payer['identification'] = {
                'type': identification.get('type'),
                'number': identification.get('number'),
            }

        payload = {
            'transaction_amount': float(total_real),
            'token': request.data.get('token'),
            'description': f'Compra Reveste - Pedido #{pedido.id}',
            'installments': int(request.data.get('installments', 1)),
            'payment_method_id': request.data.get('payment_method_id'),
            'external_reference': str(pedido.id),
            'payer': payer,
        }

        notification_url = getattr(settings, 'MERCADO_PAGO_WEBHOOK_URL', None)
        if notification_url:
            payload['notification_url'] = notification_url

        issuer_id = request.data.get('issuer_id')
        if issuer_id:
            payload['issuer_id'] = issuer_id

        return payload

    @staticmethod
    def _criar_pagamento_mp(payload):
        token = settings.MERCADO_PAGO_ACCESS_TOKEN
        if not token:
            return None, {'detail': 'Token do Mercado Pago não configurado.'}, status.HTTP_502_BAD_GATEWAY

        sdk = mercadopago.SDK(token)
        try:
            response = sdk.payment().create(payload)
        except Exception as exc:
            return (
                None,
                {'detail': f'Erro de comunicação com o gateway de pagamento: {exc}'},
                status.HTTP_502_BAD_GATEWAY,
            )

        resposta_mp = response.get('response')
        if not resposta_mp:
            return (
                None,
                {'detail': 'O Mercado Pago retornou uma resposta vazia.'},
                status.HTTP_502_BAD_GATEWAY,
            )

        return resposta_mp, None, None

    @staticmethod
    def _atualizar_pedido_nao_aprovado(pedido, mp_id, mp_status, status_detail):
        pedido.mercado_pago_payment_id = str(mp_id) if mp_id else pedido.mercado_pago_payment_id
        pedido.mercado_pago_status = mp_status
        pedido.mercado_pago_status_detail = status_detail
        pedido.status = 'CANCELADO' if mp_status in {'rejected', 'cancelled'} else 'AGUARDANDO_PAGAMENTO'
        pedido.save(
            update_fields=[
                'status',
                'mercado_pago_payment_id',
                'mercado_pago_status',
                'mercado_pago_status_detail',
                'atualizado_em',
            ]
        )

    @staticmethod
    def _resposta_mp_pagamento(mp_id, mp_status, status_detail, pedido_id):
        return {
            'id': mp_id,
            'status': mp_status,
            'status_detail': status_detail,
            'pedido_id': pedido_id,
        }

    def _obter_pedido(self, request, pedido_id):
        try:
            return Pedido.objects.select_for_update().get(id=pedido_id, usuario=request.user)
        except Pedido.DoesNotExist:
            return None

    def _responder_pagamento(self, pedido, resposta_mp):
        mp_status = resposta_mp.get('status')
        mp_id = resposta_mp.get('id')

        if mp_status == 'approved':
            try:
                confirmar_pagamento(
                    pedido_id=pedido.id,
                    payment_id=mp_id,
                    payment_status=mp_status,
                    status_detail=resposta_mp.get('status_detail'),
                )
            except ValueError as error:
                return Response({'detail': str(error)}, status=status.HTTP_409_CONFLICT)

            return Response(
                self._resposta_mp_pagamento(
                    mp_id,
                    mp_status,
                    resposta_mp.get('status_detail'),
                    pedido.id,
                ),
                status=status.HTTP_200_OK,
            )

        pedido_atualizado = Pedido.objects.select_for_update().get(id=pedido.id)
        self._atualizar_pedido_nao_aprovado(
            pedido_atualizado,
            mp_id,
            mp_status,
            resposta_mp.get('status_detail'),
        )
        return Response(
            self._resposta_mp_pagamento(
                mp_id,
                mp_status,
                resposta_mp.get('status_detail'),
                pedido_atualizado.id,
            ),
            status=status.HTTP_200_OK,
        )

    def _processar_pagamento_do_pedido(self, request, pedido_id):
        pedido = self._obter_pedido(request, pedido_id)
        if pedido is None:
            return {'status': 404, 'payload': {'detail': 'Pedido não encontrado.'}}

        if pedido.status == 'PAGO':
            return {'status': 400, 'payload': {'detail': 'Este pedido já consta como pago.'}}

        total_real = sum(Decimal(str(item.preco)) for item in pedido.itens.all())
        payload = self._montar_payload_pagamento(request, pedido, total_real)
        resposta_mp, erro, erro_status = self._criar_pagamento_mp(payload)

        if erro:
            return {'status': erro_status, 'payload': erro}

        return {'status': 200, 'payload': self._responder_pagamento(pedido, resposta_mp).data}

    def post(self, request):
        pedido_id = request.data.get('pedido_id')
        if not pedido_id:
            return Response(
                {'detail': 'ID do pedido é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            resultado = self._processar_pagamento_do_pedido(request, pedido_id)

        if resultado is None:
            return Response(
                {'detail': 'Pagamento não processado.'},
                status=status.HTTP_200_OK,
            )

        return Response(resultado['payload'], status=resultado['status'])
