import mercadopago

from django.conf import settings

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Pedido

from .services import confirmar_pagamento


class MercadoPagoWebhookView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        payment_type = (
            request.data.get('type')
            or request.query_params.get('type')
        )

        payment_data = request.data.get(
            'data',
            {}
        )

        payment_id = (
            payment_data.get('id')
            or request.query_params.get(
                'data.id'
            )
        )

        # Nem toda notificação recebida precisa
        # ser processada como pagamento.
        if payment_type != 'payment':
            return Response(
                {
                    'detail':
                    'Notificação ignorada.'
                },
                status=status.HTTP_200_OK
            )

        if not payment_id:
            return Response(
                {
                    'detail':
                    'ID do pagamento não informado.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            sdk = mercadopago.SDK(
                settings.MERCADO_PAGO_ACCESS_TOKEN
            )

            payment_response = (
                sdk.payment().get(
                    payment_id
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
                        'Pagamento não encontrado.'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            pedido_id = pagamento.get(
                'external_reference'
            )

            if not pedido_id:
                return Response(
                    {
                        'detail':
                        'Pagamento sem pedido associado.'
                    },
                    status=status.HTTP_200_OK
                )

            pedido = (
                Pedido.objects
                .filter(
                    id=pedido_id
                )
                .first()
            )

            if not pedido:
                return Response(
                    {
                        'detail':
                        'Pedido não encontrado.'
                    },
                    status=status.HTTP_200_OK
                )

            pagamento_status = (
                pagamento.get('status')
            )

            if pagamento_status == 'approved':

                confirmar_pagamento(
                    pedido.id
                )

            return Response(
                {
                    'detail':
                    'Webhook processado.',
                    'pedido_id':
                    pedido.id,
                    'payment_id':
                    payment_id,
                    'status':
                    pagamento_status,
                },
                status=status.HTTP_200_OK
            )

        except Exception as error:

            print(
                'Erro no webhook Mercado Pago:',
                error
            )

            # Retornamos 200 para evitar várias
            # tentativas automáticas em um erro
            # interno que precisa ser investigado.
            return Response(
                {
                    'detail':
                    'Erro ao processar webhook.'
                },
                status=status.HTTP_200_OK
            )