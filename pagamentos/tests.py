from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase, APIClient

from core.models import Categoria, ItemPedido, Pedido, Produto, Venda


@override_settings(MERCADO_PAGO_ACCESS_TOKEN='TEST-ACCESS-TOKEN')
class CheckoutPaymentTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(email='buyer@example.com', password='test-pass', name='Buyer')
        self.seller = User.objects.create_user(email='seller@example.com', password='test-pass', name='Seller', role='seller')
        self.client.force_authenticate(self.buyer)
        category = Categoria.objects.create(nome='Roupas')
        self.product = Produto.objects.create(
            nome='Jaqueta teste', descricao='Peça de teste', preco=Decimal('75.00'),
            marca='Reveste', condicao='usado', categoria=category, vendedor=self.seller,
        )
        self.order = Pedido.objects.create(usuario=self.buyer)
        ItemPedido.objects.create(
            pedido=self.order, produto=self.product, quantidade=1, preco=self.product.preco,
            nome=self.product.nome,
        )

    def test_cart_response_matches_frontend_contract(self):
        response = self.client.get('/api/carrinho/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pedido_id'], self.order.id)
        self.assertEqual(response.data['itens'][0]['produto'], self.product.id)
        self.assertEqual(Decimal(response.data['total']), Decimal('75.00'))

    def test_checkout_reserves_product_and_returns_server_total(self):
        response = self.client.post('/api/pagamentos/criar-checkout/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pedido_id'], self.order.id)
        self.assertEqual(Decimal(str(response.data['amount'])), Decimal('75.00'))
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, 'AGUARDANDO_PAGAMENTO')
        self.assertEqual(self.product.reserva_pedido_id, self.order.id)
        self.assertIsNotNone(self.product.reservado_ate)

    @patch('pagamentos.views.requests.request')
    def test_approved_pix_confirms_order_and_records_sale(self, request_mock):
        checkout = self.client.post('/api/pagamentos/criar-checkout/', {}, format='json')
        self.assertEqual(checkout.status_code, 200)
        request_mock.return_value = Mock(
            ok=True,
            status_code=201,
            json=Mock(return_value={
                'id': 123456,
                'status': 'approved',
                'status_detail': 'accredited',
                'currency_id': 'BRL',
                'transaction_amount': 75.00,
                'external_reference': str(self.order.id),
                'payment_method_id': 'pix',
                'point_of_interaction': {'transaction_data': {'qr_code': 'pix-copia-cola', 'qr_code_base64': 'cXJjb2Rl'}},
            }),
        )
        response = self.client.post('/api/pagamentos/processar/', {
            'pedido_id': self.order.id,
            'payment_method_id': 'pix',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, 'PAGO')
        self.assertFalse(self.product.disponivel)
        self.assertEqual(self.order.mercado_pago_payment_id, '123456')
        self.assertTrue(Venda.objects.filter(pedido=self.order).exists())
        self.assertEqual(response.data['qr_code'], 'pix-copia-cola')

    @patch('pagamentos.views.requests.request')
    def test_boleto_requires_address_and_returns_ticket_url(self, request_mock):
        checkout = self.client.post('/api/pagamentos/criar-checkout/', {}, format='json')
        self.assertEqual(checkout.status_code, 200)
        request_mock.return_value = Mock(
            ok=True,
            status_code=201,
            json=Mock(return_value={
                'id': 789012,
                'status': 'pending',
                'status_detail': 'pending_waiting_payment',
                'currency_id': 'BRL',
                'transaction_amount': 75.00,
                'external_reference': str(self.order.id),
                'payment_method_id': 'bolbradesco',
                'transaction_details': {'external_resource_url': 'https://example.test/boleto'},
            }),
        )
        response = self.client.post('/api/pagamentos/processar/', {
            'pedido_id': self.order.id,
            'payment_method_id': 'bolbradesco',
            'payer': {
                'first_name': 'Buyer',
                'last_name': 'Teste',
                'identification': {'type': 'CPF', 'number': '123.456.789-09'},
                'address': {
                    'street_name': 'Rua de Teste',
                    'street_number': '123',
                    'neighborhood': 'Centro',
                    'city': 'Araquari',
                    'federal_unit': 'SC',
                    'zip_code': '89245000',
                },
            },
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['ticket_url'], 'https://example.test/boleto')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'AGUARDANDO_PAGAMENTO')

    def test_customer_cannot_read_another_users_order(self):
        other = get_user_model().objects.create_user(
            email='other@example.com', password='test-pass', name='Other',
        )
        self.client.force_authenticate(other)
        response = self.client.get(f'/api/pedidos/{self.order.id}/')
        self.assertEqual(response.status_code, 404)
