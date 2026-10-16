import hashlib
import hmac
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from core.models import ItemPedido, Pedido, Produto, Venda

User = get_user_model()


class MercadoPagoWebhookTests(TestCase):
    secret = 'webhook-secret-test'

    def setUp(self):
        buyer = User.objects.create_user(email='webhook-buyer@example.com', password='test-pass', name='Buyer')
        seller = User.objects.create_user(email='webhook-seller@example.com', password='test-pass', name='Seller')
        self.product = Produto.objects.create(
            nome='Calca vintage', descricao='Boa', preco=Decimal('89.90'),
            marca='Reveste', condicao='usado', user=seller, disponivel=True,
        )
        self.order = Pedido.objects.create(usuario=buyer, status='AGUARDANDO_PAGAMENTO')
        self.product.reserva_pedido = self.order
        self.product.reservado_ate = timezone.now() + timedelta(minutes=30)
        self.product.save(update_fields=['reserva_pedido', 'reservado_ate'])
        ItemPedido.objects.create(
            pedido=self.order, produto=self.product, quantidade=1,
            preco=self.product.preco, nome=self.product.nome,
        )

    def signature(self, payment_id, request_id='request-123', timestamp='1700000000'):
        manifest = f'id:{payment_id};request-id:{request_id};ts:{timestamp};'
        digest = hmac.new(self.secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        return f'ts={timestamp},v1={digest}'

    def send_webhook(self, payment_id, payload):
        with patch('pagamentos.webhooks.mercadopago.SDK') as sdk:
            sdk.return_value.payment.return_value.get.return_value = {'response': payload}
            return APIClient().post(
                f'/api/pagamentos/webhook/?type=payment&data.id={payment_id}',
                data={'type': 'payment', 'data': {'id': payment_id}},
                format='json',
                HTTP_X_SIGNATURE=self.signature(payment_id),
                HTTP_X_REQUEST_ID='request-123',
            )

    @override_settings(MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN', MERCADO_PAGO_WEBHOOK_SECRET=secret)
    def test_approved_webhook_marks_order_paid_and_creates_sale(self):
        response = self.send_webhook('payment-123', {
            'id': 'payment-123', 'status': 'approved', 'status_detail': 'accredited',
            'external_reference': str(self.order.id), 'transaction_amount': 89.90, 'currency_id': 'BRL',
        })
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, 'PAGO')
        self.assertFalse(self.product.disponivel)
        self.assertEqual(Venda.objects.filter(pedido=self.order).count(), 1)

    @override_settings(MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN', MERCADO_PAGO_WEBHOOK_SECRET=secret)
    def test_pending_webhook_does_not_mark_order_paid(self):
        response = self.send_webhook('payment-456', {
            'id': 'payment-456', 'status': 'pending', 'status_detail': 'pending_waiting_payment',
            'external_reference': str(self.order.id), 'transaction_amount': 89.90, 'currency_id': 'BRL',
        })
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'AGUARDANDO_PAGAMENTO')
        self.assertTrue(self.product.disponivel)
        self.assertFalse(Venda.objects.filter(pedido=self.order).exists())

    @override_settings(MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN', MERCADO_PAGO_WEBHOOK_SECRET=secret)
    def test_wrong_amount_webhook_does_not_mark_order_paid(self):
        response = self.send_webhook('payment-789', {
            'id': 'payment-789', 'status': 'approved', 'status_detail': 'accredited',
            'external_reference': str(self.order.id), 'transaction_amount': 1.00, 'currency_id': 'BRL',
        })
        self.assertEqual(response.status_code, 409)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'AGUARDANDO_PAGAMENTO')
        self.assertTrue(self.product.disponivel)
        self.assertFalse(Venda.objects.filter(pedido=self.order).exists())

    @override_settings(MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN', MERCADO_PAGO_WEBHOOK_SECRET=secret)
    def test_wrong_external_reference_does_not_confirm_order(self):
        response = self.send_webhook('payment-999', {
            'id': 'payment-999', 'status': 'approved', 'status_detail': 'accredited',
            'external_reference': '999999', 'transaction_amount': 89.90, 'currency_id': 'BRL',
        })
        self.assertEqual(response.status_code, 404)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'AGUARDANDO_PAGAMENTO')
