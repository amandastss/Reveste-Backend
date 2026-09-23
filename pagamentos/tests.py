import hashlib
import hmac
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import ItemPedido, Pedido, Produto, Venda

User = get_user_model()


class CriarCheckoutViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='comprador@example.com',
            password='senha123',
            name='Comprador',
        )

        self.vendedor = User.objects.create_user(
            email='vendedor@example.com',
            password='senha123',
            name='Vendedor',
        )

        self.produto = Produto.objects.create(
            nome='Camisa vintage',
            descricao='Boa',
            preco=Decimal('129.90'),
            marca='Reveste',
            condicao='usado',
            user=self.vendedor,
            disponivel=True,
        )

        self.pedido = Pedido.objects.create(usuario=self.user, status='PENDENTE')
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.produto,
            quantidade=1,
            preco=self.produto.preco,
            nome=self.produto.nome,
        )

    @override_settings(MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN', FRONTEND_URL='http://localhost:5173')
    @patch('pagamentos.views.mercadopago.SDK')
    def test_checkout_retorna_init_point_e_payload_do_mercado_pago(self, mock_sdk):
        mock_sdk.return_value.preference.return_value.create.return_value = {
            'response': {
                'id': 'pref_123456',
                'init_point': 'https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=pref_123456',
                'sandbox_init_point': 'https://sandbox.mercadopago.com.br/checkout/v1/redirect?pref_id=pref_123456',
            }
        }

        client = APIClient()
        client.force_authenticate(user=self.user)

        response = client.post('/api/pagamentos/criar-checkout/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('init_point', response.data)
        self.assertIn('preference_id', response.data)
        self.assertEqual(response.data['preference_id'], 'pref_123456')
        self.assertTrue(response.data['init_point'].startswith('https://'))

        payload = mock_sdk.return_value.preference.return_value.create.call_args[0][0]
        self.assertIn('notification_url', payload)
        self.assertIn('back_urls', payload)
        self.assertEqual(payload['external_reference'], str(self.pedido.id))
        self.assertIn(f'pedido_id={self.pedido.id}', payload['back_urls']['success'])
        self.assertIn('status=approved', payload['back_urls']['success'])
        self.assertIn(f'pedido_id={self.pedido.id}', payload['back_urls']['failure'])
        self.assertIn('status=rejected', payload['back_urls']['failure'])
        self.assertIn(f'pedido_id={self.pedido.id}', payload['back_urls']['pending'])
        self.assertIn('status=pending', payload['back_urls']['pending'])


class MercadoPagoWebhookTests(TestCase):
    webhook_secret = 'webhook-secret-test'

    def setUp(self):
        self.comprador = User.objects.create_user(
            email='comprador-webhook@example.com',
            password='senha123',
            name='Comprador Webhook',
        )
        self.vendedor = User.objects.create_user(
            email='vendedor-webhook@example.com',
            password='senha123',
            name='Vendedor Webhook',
        )
        self.produto = Produto.objects.create(
            nome='Calca vintage',
            descricao='Boa',
            preco=Decimal('89.90'),
            marca='Reveste',
            condicao='usado',
            user=self.vendedor,
            disponivel=True,
        )
        self.pedido = Pedido.objects.create(
            usuario=self.comprador,
            status='AGUARDANDO_PAGAMENTO',
        )
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.produto,
            quantidade=1,
            preco=self.produto.preco,
            nome=self.produto.nome,
        )

    def _assinatura(self, payment_id, request_id='request-123', timestamp='1700000000'):
        manifest = f'id:{payment_id};request-id:{request_id};ts:{timestamp};'
        digest = hmac.new(
            self.webhook_secret.encode(),
            manifest.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f'ts={timestamp},v1={digest}'

    @override_settings(
        MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN',
        MERCADO_PAGO_WEBHOOK_SECRET=webhook_secret,
    )
    @patch('pagamentos.webhooks.mercadopago.SDK')
    def test_webhook_aprovado_confirma_pedido_e_cria_venda(self, mock_sdk):
        mock_sdk.return_value.payment.return_value.get.return_value = {
            'response': {
                'id': 'payment_123',
                'status': 'approved',
                'status_detail': 'accredited',
                'external_reference': str(self.pedido.id),
            }
        }

        client = APIClient()
        response = client.post(
            '/api/pagamentos/webhook/?type=payment&data.id=payment_123',
            data={'type': 'payment', 'data': {'id': 'payment_123'}},
            format='json',
            HTTP_X_SIGNATURE=self._assinatura('payment_123'),
            HTTP_X_REQUEST_ID='request-123',
        )

        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        self.produto.refresh_from_db()
        self.assertEqual(self.pedido.status, 'PAGO')
        self.assertEqual(self.pedido.mercado_pago_payment_id, 'payment_123')
        self.assertFalse(self.produto.disponivel)
        self.assertTrue(Venda.objects.filter(pedido=self.pedido).exists())

    @override_settings(
        MERCADO_PAGO_ACCESS_TOKEN='TEST_TOKEN',
        MERCADO_PAGO_WEBHOOK_SECRET=webhook_secret,
    )
    @patch('pagamentos.webhooks.mercadopago.SDK')
    def test_webhook_pendente_nao_confirma_pedido(self, mock_sdk):
        mock_sdk.return_value.payment.return_value.get.return_value = {
            'response': {
                'id': 'payment_456',
                'status': 'pending',
                'status_detail': 'pending_waiting_payment',
                'external_reference': str(self.pedido.id),
            }
        }

        client = APIClient()
        response = client.post(
            '/api/pagamentos/webhook/?type=payment&data.id=payment_456',
            data={'type': 'payment', 'data': {'id': 'payment_456'}},
            format='json',
            HTTP_X_SIGNATURE=self._assinatura('payment_456'),
            HTTP_X_REQUEST_ID='request-123',
        )

        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'AGUARDANDO_PAGAMENTO')
        self.assertEqual(self.pedido.mercado_pago_status, 'pending')
        self.assertFalse(Venda.objects.filter(pedido=self.pedido).exists())
