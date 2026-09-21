from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import ItemPedido, Pedido, Produto

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
