import hashlib
import hmac
import logging

import mercadopago
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Pedido, Produto

from .services import confirmar_pagamento

logger = logging.getLogger(__name__)


class MercadoPagoWebhookView(APIView):
    permission_classes = [AllowAny]

    @staticmethod
    def _validar_assinatura(request, payment_id):
        secret = getattr(settings, 'MERCADO_PAGO_WEBHOOK_SECRET', None)
        if not secret:
            logger.error('MERCADO_PAGO_WEBHOOK_SECRET não configurado.')
            return False

        assinatura = request.headers.get('x-signature')
        request_id = request.headers.get('x-request-id')
        if not assinatura or not request_id:
            return False

        partes = {}
        for parte in assinatura.split(','):
            chave, separador, valor = parte.partition('=')
            if separador:
                partes[chave] = valor

        timestamp = partes.get('ts')
        assinatura_recebida = partes.get('v1')
        if not timestamp or not assinatura_recebida:
            return False

        manifest = f'id:{payment_id};request-id:{request_id};ts:{timestamp};'
        assinatura_calculada = hmac.new(
            secret.encode('utf-8'),
            manifest.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(assinatura_calculada, assinatura_recebida)

    @staticmethod
    def _buscar_pagamento(payment_id):
        token = getattr(settings, 'MERCADO_PAGO_ACCESS_TOKEN', None)
        if not token:
            logger.error('MERCADO_PAGO_ACCESS_TOKEN não configurado.')
            return None
        try:
            response = mercadopago.SDK(token).payment().get(payment_id)
        except Exception:
            logger.exception('Erro ao consultar pagamento no Mercado Pago.')
            return None
        return response.get('response') if isinstance(response, dict) else None

    def _preparar_notificacao(self, request):
        payment_type = request.data.get('type') or request.query_params.get('type')
        if payment_type != 'payment':
            return None, Response({'detail': 'Notificação ignorada.'}, status=status.HTTP_200_OK)

        payment_data = request.data.get('data') or {}
        payment_id = payment_data.get('id') or request.query_params.get('data.id')
        if not payment_id:
            return None, Response(
                {'detail': 'ID do pagamento não informado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not self._validar_assinatura(request, str(payment_id)):
            logger.warning('Webhook Mercado Pago rejeitado: assinatura inválida.')
            return None, Response(
                {'detail': 'Assinatura do webhook inválida.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        pagamento = self._buscar_pagamento(payment_id)
        if not pagamento:
            return None, Response(
                {'detail': 'Pagamento não encontrado no Mercado Pago.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if str(pagamento.get('id')) != str(payment_id):
            return None, Response(
                {'detail': 'O ID retornado pelo Mercado Pago não corresponde à notificação.'},
                status=status.HTTP_409_CONFLICT,
            )
        pedido_id = pagamento.get('external_reference')
        if not pedido_id:
            return None, Response(
                {'detail': 'Pagamento sem pedido associado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return {'payment_id': str(payment_id), 'pagamento': pagamento, 'pedido_id': str(pedido_id)}, None

    @staticmethod
    def _confirmar_pagamento_aprovado(pedido, dados):
        pagamento = dados['pagamento']
        try:
            confirmar_pagamento(
                pedido_id=pedido.id,
                payment_id=dados['payment_id'],
                payment_status=pagamento.get('status'),
                status_detail=pagamento.get('status_detail'),
                transaction_amount=pagamento.get('transaction_amount'),
                currency_id=pagamento.get('currency_id'),
            )
        except ValueError as error:
            logger.warning('Pagamento aprovado não pôde confirmar o pedido %s: %s', pedido.id, error)
            return Response({'detail': str(error)}, status=status.HTTP_409_CONFLICT)
        except Exception:
            logger.exception('Erro ao confirmar pedido %s após pagamento aprovado.', pedido.id)
            return Response(
                {'detail': 'Erro interno ao confirmar o pagamento.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return None

    def post(self, request):
        dados, erro_response = self._preparar_notificacao(request)
        if erro_response:
            return erro_response

        pagamento = dados['pagamento']
        payment_id = dados['payment_id']
        pagamento_status = pagamento.get('status')
        pedido = Pedido.objects.filter(id=dados['pedido_id']).first()
        if pedido is None:
            return Response(
                {'detail': 'Pedido associado ao pagamento não foi encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if str(pagamento.get('external_reference')) != str(pedido.id):
            return Response(
                {'detail': 'A referência do pagamento não corresponde ao pedido.'},
                status=status.HTTP_409_CONFLICT,
            )

        if pagamento_status == 'approved':
            erro_response = self._confirmar_pagamento_aprovado(pedido, dados)
            if erro_response:
                return erro_response
        else:
            with transaction.atomic():
                pedido = Pedido.objects.select_for_update().get(id=pedido.id)
                # Uma notificação atrasada não pode substituir a confirmação já obtida.
                if pedido.status != 'PAGO':
                    pedido.mercado_pago_payment_id = payment_id
                    pedido.mercado_pago_status = pagamento_status
                    pedido.mercado_pago_status_detail = pagamento.get('status_detail')
                    fields = [
                        'mercado_pago_payment_id',
                        'mercado_pago_status',
                        'mercado_pago_status_detail',
                        'atualizado_em',
                    ]
                    if pagamento_status in {'rejected', 'cancelled'}:
                        pedido.status = 'CANCELADO'
                        fields.append('status')
                        Produto.objects.filter(reserva_pedido=pedido).update(
                            reserva_pedido=None,
                            reservado_ate=None,
                        )
                    pedido.save(update_fields=fields)

        return Response({
            'detail': 'Webhook processado.',
            'pedido_id': pedido.id,
            'payment_id': payment_id,
            'status': pagamento_status,
        }, status=status.HTTP_200_OK)
