from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import ItemPedido, Pedido, Produto

User = get_user_model()


class PurchaseApiPermissionTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            password='test-pass',
            name='Buyer',
        )
        self.other_buyer = User.objects.create_user(
            email='other@example.com',
            password='test-pass',
            name='Other Buyer',
        )
        self.seller = User.objects.create_user(
            email='seller@example.com',
            password='test-pass',
            name='Seller',
        )
        self.product = Produto.objects.create(
            nome='Camisa vintage',
            descricao='Boa',
            preco=Decimal('129.90'),
            marca='Reveste',
            condicao='usado',
            user=self.seller,
            disponivel=True,
        )
        self.own_order = Pedido.objects.create(usuario=self.buyer)
        self.other_order = Pedido.objects.create(usuario=self.other_buyer)
        self.own_item = ItemPedido.objects.create(
            pedido=self.own_order,
            produto=self.product,
            quantidade=1,
            preco=self.product.preco,
            nome=self.product.nome,
        )
        self.other_item = ItemPedido.objects.create(
            pedido=self.other_order,
            produto=self.product,
            quantidade=1,
            preco=self.product.preco,
            nome=self.product.nome,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)

    def test_item_list_contains_only_items_from_current_users_orders(self):
        response = self.client.get('/api/itens-pedido/')

        self.assertEqual(response.status_code, 200)
        returned_ids = {item['id'] for item in response.data['results']}
        self.assertEqual(returned_ids, {self.own_item.id})

    def test_user_cannot_retrieve_another_users_order_item(self):
        response = self.client.get(f'/api/itens-pedido/{self.other_item.id}/')

        self.assertEqual(response.status_code, 404)

    def test_item_endpoint_does_not_allow_writes(self):
        response = self.client.post('/api/itens-pedido/', {}, format='json')

        self.assertEqual(response.status_code, 405)

    def test_order_endpoint_does_not_allow_direct_creation(self):
        response = self.client.post('/api/pedidos/', {}, format='json')

        self.assertEqual(response.status_code, 405)

    def test_order_endpoint_does_not_allow_direct_status_changes(self):
        response = self.client.patch(
            f'/api/pedidos/{self.own_order.id}/',
            {'status': 'PAGO'},
            format='json',
        )

        self.assertEqual(response.status_code, 405)

    def test_order_history_contains_only_current_users_orders(self):
        response = self.client.get('/api/pedidos/')

        self.assertEqual(response.status_code, 200)
        returned_ids = {order['id'] for order in response.data['results']}
        self.assertEqual(returned_ids, {self.own_order.id})
