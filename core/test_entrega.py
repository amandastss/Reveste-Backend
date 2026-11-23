from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Pedido, Produto, Venda

User = get_user_model()


class AtualizarEntregaPedidoTests(TestCase):
    def setUp(self):
        self.comprador = User.objects.create_user(
            email='comprador-entrega@example.com',
            password='test-pass',
            name='Comprador',
        )
        self.vendedor = User.objects.create_user(
            email='vendedor-entrega@example.com',
            password='test-pass',
            name='Vendedor',
        )
        self.outro_vendedor = User.objects.create_user(
            email='outro-vendedor@example.com',
            password='test-pass',
            name='Outro vendedor',
        )
        self.produto = Produto.objects.create(
            nome='Jaqueta vintage',
            descricao='Jaqueta em bom estado',
            preco=Decimal('120.00'),
            marca='Reveste',
            user=self.vendedor,
            disponivel=False,
        )
        self.pedido = Pedido.objects.create(
            usuario=self.comprador,
            status='PAGO',
            status_entrega='AGUARDANDO_PREPARACAO',
            endereco_entrega={
                'cep': '89245000',
                'rua': 'Rua Teste',
                'numero': '10',
                'bairro': 'Centro',
                'cidade': 'Araquari',
                'estado': 'SC',
            },
        )
        Venda.objects.create(pedido=self.pedido, vendedor=self.vendedor)
        self.client = APIClient()

    def test_vendedor_avanca_entrega_em_ordem(self):
        self.client.force_authenticate(user=self.vendedor)
        response = self.client.patch(
            f'/api/pedidos/{self.pedido.id}/entrega/',
            {'status_entrega': 'ENVIADO'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status_entrega, 'ENVIADO')

    def test_outro_vendedor_nao_pode_alterar_entrega(self):
        self.client.force_authenticate(user=self.outro_vendedor)
        response = self.client.patch(
            f'/api/pedidos/{self.pedido.id}/entrega/',
            {'status_entrega': 'ENVIADO'},
            format='json',
        )
        self.assertEqual(response.status_code, 404)

    def test_nao_permite_pular_etapas_da_entrega(self):
        self.client.force_authenticate(user=self.vendedor)
        response = self.client.patch(
            f'/api/pedidos/{self.pedido.id}/entrega/',
            {'status_entrega': 'EM_TRANSITO'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
