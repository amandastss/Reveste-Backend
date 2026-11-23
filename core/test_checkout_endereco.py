from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import ItemPedido, Pedido, Produto

User = get_user_model()


class EnderecoCheckoutTests(TestCase):
    def setUp(self):
        self.comprador = User.objects.create_user(
            email='comprador-endereco@example.com',
            password='test-pass',
            name='Comprador',
        )
        self.vendedor = User.objects.create_user(
            email='vendedor-endereco@example.com',
            password='test-pass',
            name='Vendedor',
        )
        self.produto = Produto.objects.create(
            nome='Camisa vintage',
            descricao='Camisa em bom estado',
            preco=Decimal('75.00'),
            marca='Reveste',
            user=self.vendedor,
            disponivel=True,
        )
        self.pedido = Pedido.objects.create(usuario=self.comprador, status='PENDENTE')
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.produto,
            quantidade=1,
            preco=self.produto.preco,
            nome=self.produto.nome,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.comprador)

    def test_checkout_salva_endereco_no_perfil_e_copia_no_pedido(self):
        endereco = {
            'cep': '89245000',
            'rua': 'Rua das Flores',
            'numero': '123',
            'complemento': 'Casa 2',
            'bairro': 'Centro',
            'cidade': 'Araquari',
            'estado': 'sc',
        }
        response = self.client.post(
            '/api/carrinho/finalizar/',
            {'endereco_entrega': endereco},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.comprador.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.comprador.endereco_entrega['estado'], 'SC')
        self.assertEqual(self.pedido.endereco_entrega['rua'], 'Rua das Flores')
        self.assertEqual(self.pedido.endereco_entrega['numero'], '123')
        self.assertEqual(self.pedido.status, 'PENDENTE')
