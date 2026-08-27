from decimal import Decimal
import mercadopago
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from core.models import Pedido

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
                {'detail': 'Nenhum pedido pendente foi encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        itens = list(pedido.itens.all())

        if not itens:
            return Response(
                {'detail': 'O carrinho está vazio.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        preference_items = []

        for item in itens:
            produto = item.produto

            if not produto.disponivel:
                return Response(
                    {'detail': f'A peça "{produto.nome}" não está mais disponível.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if produto.user == request.user:
                return Response(
                    {'detail': 'Você não pode comprar sua própria peça.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            preference_items.append({
                'id': str(produto.id),
                'title': produto.nome,
                'quantity': 1,
                'unit_price': float(Decimal(produto.preco)),
                'currency_id': 'BRL',
            })

        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

        preference_data = {
            'items': preference_items,
            'external_reference': str(pedido.id),
            'back_urls': {
                'success': f'{settings.FRONTEND_URL}/pagamento/sucesso',
                'failure': f'{settings.FRONTEND_URL}/pagamento/erro',
                'pending': f'{settings.FRONTEND_URL}/pagamento/pendente',
            },
            'auto_return': 'approved',
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response['response']

        # Atualização do status e salvamento do ID da preferência
        pedido.status = 'AGUARDANDO_PAGAMENTO'
        pedido.mercado_pago_preference_id = preference['id']
        pedido.save(
            update_fields=[
                'status',
                'mercado_pago_preference_id'
            ]
        )

        checkout_url = (
            preference.get('sandbox_init_point') or preference.get('init_point')
        )

        return Response({
            'pedido_id': pedido.id,
            'checkout_url': checkout_url,
            'preference_id': preference['id'],
        })