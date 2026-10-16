from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import ItemPedido, Pedido, Produto, Venda

User = get_user_model()


class PaymentFlowTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email='buyer@example.com', password='test-pass', name='Buyer')
        self.seller = User.objects.create_user(email='seller@example.com', password='test-pass', name='Seller')
        self.product = Produto.objects.create(
            nome='Camisa vintage', descricao='Boa', preco=Decimal('129.90'),
            marca='Reveste', condicao='usado', user=self.seller, disponivel=True,
        )
        self.order = Pedido.objects.create(usuario=self.buyer, status='PENDENTE')
        ItemPedido.objects.create(
            pedido=self.order, produto=self.product, quantidade=1,
            preco=self.product.preco, nome=self.product.nome,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)

    def test_checkout_prepares_brick_without_checkout_pro_preference(self):
        with patch('pagamentos.views.mercadopago.SDK') as sdk:
            response = self.client.post('/api/pagamentos/criar-checkout/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pedido_id'], self.order.id)
        self.assertEqual(response.data['status'], 'AGUARDANDO_PAGAMENTO')
        self.assertEqual(response.data['amount'], 129.9)
        self.assertEqual(response.data['payer_email'], self.buyer.email)
        self.assertNotIn('init_point', response.data)
        self.assertNotIn('preference_id', response.data)
        sdk.assert_not_called()

    def test_checkout_rejects_unavailable_product(self):
        self.product.disponivel = False
        self.product.save(update_fields=['disponivel'])
        response = self.client.post('/api/pagamentos/criar-checkout/')
        self.assertEqual(response.status_code, 409)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PENDENTE')

    def test_checkout_reserves_unique_piece_for_first_buyer(self):
        first_response = self.client.post('/api/pagamentos/criar-checkout/')
        self.assertEqual(first_response.status_code, 200)

        other_buyer = User.objects.create_user(
            email='other-buyer@example.com', password='test-pass', name='Other Buyer'
        )
        other_order = Pedido.objects.create(usuario=other_buyer, status='PENDENTE')
        ItemPedido.objects.create(
            pedido=other_order, produto=self.product, quantidade=1,
            preco=self.product.preco, nome=self.product.nome,
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other_buyer)
        second_response = other_client.post('/api/pagamentos/criar-checkout/')

        self.assertEqual(second_response.status_code, 409)
        self.product.refresh_from_db()
        self.assertEqual(self.product.reserva_pedido_id, self.order.id)

    @override_settings(MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN')
    @patch('pagamentos.views.mercadopago.SDK')
    def test_approved_payment_confirms_order_and_sale(self, sdk):
        self.client.post('/api/pagamentos/criar-checkout/')
        sdk.return_value.payment.return_value.create.return_value = {'response': {
            'id': 'payment-123', 'status': 'approved', 'status_detail': 'accredited',
            'external_reference': str(self.order.id), 'transaction_amount': 129.90, 'currency_id': 'BRL',
        }}
        response = self.client.post('/api/pagamentos/processar/', {
            'pedido_id': self.order.id, 'token': 'mock-token',
            'installments': 1, 'payment_method_id': 'visa',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, 'PAGO')
        self.assertFalse(self.product.disponivel)
        self.assertEqual(Venda.objects.filter(pedido=self.order).count(), 1)

    @override_settings(MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN')
    @patch('pagamentos.views.mercadopago.SDK')
    def test_pending_payment_does_not_mark_order_paid(self, sdk):
        self.client.post('/api/pagamentos/criar-checkout/')
        sdk.return_value.payment.return_value.create.return_value = {'response': {
            'id': 'payment-pending', 'status': 'pending', 'status_detail': 'pending_waiting_payment',
            'external_reference': str(self.order.id), 'transaction_amount': 129.90, 'currency_id': 'BRL',
        }}
        response = self.client.post('/api/pagamentos/processar/', {
            'pedido_id': self.order.id, 'token': 'mock-token',
            'installments': 1, 'payment_method_id': 'visa',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'AGUARDANDO_PAGAMENTO')
        self.assertTrue(self.product.disponivel)
        self.assertFalse(Venda.objects.filter(pedido=self.order).exists())

    @override_settings(MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN')
    @patch('pagamentos.views.mercadopago.SDK')
    def test_wrong_approved_amount_does_not_confirm_order(self, sdk):
        self.client.post('/api/pagamentos/criar-checkout/')
        sdk.return_value.payment.return_value.create.return_value = {'response': {
            'id': 'payment-wrong', 'status': 'approved', 'status_detail': 'accredited',
            'external_reference': str(self.order.id), 'transaction_amount': 1.00, 'currency_id': 'BRL',
        }}
        response = self.client.post('/api/pagamentos/processar/', {
            'pedido_id': self.order.id, 'token': 'mock-token',
            'installments': 1, 'payment_method_id': 'visa',
        }, format='json')
        self.assertEqual(response.status_code, 409)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'AGUARDANDO_PAGAMENTO')
        self.assertTrue(self.product.disponivel)
        self.assertFalse(Venda.objects.filter(pedido=self.order).exists())

    @override_settings(MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN')
    @patch('pagamentos.views.mercadopago.SDK')
    def test_rejected_payment_cancels_order_and_releases_reservation(self, sdk):
        self.client.post('/api/pagamentos/criar-checkout/')
        sdk.return_value.payment.return_value.create.return_value = {'response': {
            'id': 'payment-rejected', 'status': 'rejected', 'status_detail': 'cc_rejected',
            'external_reference': str(self.order.id),
        }}
        response = self.client.post('/api/pagamentos/processar/', {
            'pedido_id': self.order.id, 'token': 'mock-token',
            'installments': 1, 'payment_method_id': 'visa',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, 'CANCELADO')
        self.assertTrue(self.product.disponivel)
        self.assertIsNone(self.product.reserva_pedido_id)
        self.assertFalse(Venda.objects.filter(pedido=self.order).exists())

    def test_order_status_endpoint_returns_status_for_checkout(self):
        response = self.client.get(f'/api/pedidos/{self.order.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.order.id)
        self.assertEqual(response.data['status'], 'PENDENTE')
        self.assertIn('criado_em', response.data)

    def test_process_rejects_order_not_waiting_for_payment(self):
        response = self.client.post('/api/pagamentos/processar/', {
            'pedido_id': self.order.id, 'token': 'mock-token',
            'installments': 1, 'payment_method_id': 'visa',
        }, format='json')
        self.assertEqual(response.status_code, 409)
