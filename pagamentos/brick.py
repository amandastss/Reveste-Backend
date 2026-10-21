from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from .views import ProcessarPagamentoView


class ProcessarPagamentoBrickView(ProcessarPagamentoView):
    """Processa cartão, Pix e boleto enviados pelo Payment Brick."""

    @staticmethod
    def _payload_pagamento(request, pedido, total):
        payment_method_id = request.data.get('payment_method_id')
        token = request.data.get('token')
        if not isinstance(payment_method_id, str) or not payment_method_id.strip():
            return None, 'Método de pagamento obrigatório.'

        payment_method_id = payment_method_id.strip()
        payer_data = request.data.get('payer') or {}
        if not isinstance(payer_data, dict):
            payer_data = {}

        payer = {'email': request.user.email}
        identification = payer_data.get('identification') or {}
        if isinstance(identification, dict) and identification.get('type') and identification.get('number'):
            payer['identification'] = {
                'type': str(identification['type']),
                'number': str(identification['number']),
            }

        payload = {
            'transaction_amount': float(total),
            'description': f'Compra Reveste - Pedido #{pedido.id}',
            'payment_method_id': payment_method_id,
            'external_reference': str(pedido.id),
            'payer': payer,
        }

        if payment_method_id == 'pix':
            # O Pix exige documento do pagador, mas não token de cartão.
            if not (isinstance(identification, dict) and identification.get('type') and identification.get('number')):
                return None, 'Informe o CPF ou documento solicitado pelo Mercado Pago para pagar com Pix.'
        elif payment_method_id == 'bolbradesco':
            # O boleto precisa dos dados de endereço exigidos pelo Mercado Pago.
            address = payer_data.get('address') or {}
            if not isinstance(address, dict):
                address = {}
            required_address = (
                'street_name', 'street_number', 'neighborhood',
                'city', 'federal_unit', 'zip_code',
            )
            if any(not str(address.get(field, '')).strip() for field in required_address):
                return None, 'Para gerar o boleto, preencha o endereço completo do pagador no formulário.'
            payer['address'] = {field: str(address[field]).strip() for field in required_address}
            if not (isinstance(identification, dict) and identification.get('type') and identification.get('number')):
                return None, 'Informe o CPF ou documento solicitado pelo Mercado Pago para gerar o boleto.'
            for field in ('first_name', 'last_name'):
                value = payer_data.get(field)
                if value:
                    payer[field] = str(value).strip()
        else:
            # Todos os demais métodos aceitos neste checkout são cartões.
            if not isinstance(token, str) or not token.strip():
                return None, 'O Mercado Pago não gerou o token do cartão. Confira os dados e tente novamente.'
            try:
                installments = int(request.data.get('installments', 1))
            except (TypeError, ValueError):
                installments = 0
            if installments < 1:
                return None, 'Quantidade de parcelas inválida.'
            payload['token'] = token.strip()
            payload['installments'] = installments
            issuer_id = request.data.get('issuer_id')
            if issuer_id:
                payload['issuer_id'] = issuer_id

        notification_url = getattr(settings, 'MERCADO_PAGO_WEBHOOK_URL', None)
        if notification_url:
            payload['notification_url'] = notification_url
        return payload, None

    @staticmethod
    def _resposta_pagamento(dados, pedido):
        response = ProcessarPagamentoView._resposta_pagamento(dados, pedido)
        if response.status_code != status.HTTP_200_OK or not isinstance(response.data, dict):
            return response

        # Retorna ao frontend apenas instruções de pagamento necessárias ao comprador.
        transaction_data = (
            (dados.get('point_of_interaction') or {}).get('transaction_data') or {}
        )
        transaction_details = dados.get('transaction_details') or {}
        response.data.update({
            'payment_method_id': dados.get('payment_method_id'),
            'qr_code': transaction_data.get('qr_code'),
            'qr_code_base64': transaction_data.get('qr_code_base64'),
            'ticket_url': transaction_details.get('external_resource_url'),
        })
        return response
