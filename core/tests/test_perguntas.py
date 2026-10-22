from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Notificacao, Pergunta, Produto, User


class PerguntaAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.seller = User.objects.create_user(
            email='vendedor@email.com',
            password='123456',
            name='Vendedor',
            role='seller',
        )
        self.buyer = User.objects.create_user(
            email='comprador@email.com',
            password='123456',
            name='Comprador',
            role='buyer',
        )
        self.produto = Produto.objects.create(
            nome='Camiseta',
            descricao='Camiseta de algodão',
            preco='79.90',
            marca='Reveste',
            categoria_id=None,
            user=self.seller,
        )

    def test_criar_pergunta_cria_notificacao_para_o_vendedor(self):
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(
            '/api/perguntas/',
            {'produto': self.produto.id, 'texto': 'Essa camiseta é 100% algodão?'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Pergunta.objects.filter(produto=self.produto, user=self.buyer).exists())
        self.assertTrue(
            Notificacao.objects.filter(
                usuario=self.seller,
                mensagem__icontains='Nova pergunta',
            ).exists()
        )

    def test_vendedor_pode_responder_pergunta(self):
        pergunta = Pergunta.objects.create(
            produto=self.produto,
            user=self.buyer,
            texto='Qual o tamanho ideal?',
        )

        self.client.force_authenticate(user=self.seller)
        response = self.client.patch(
            f'/api/perguntas/{pergunta.id}/responder/',
            {'resposta': 'Tamanho M para quem usa 1,60m.'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        pergunta.refresh_from_db()
        self.assertEqual(pergunta.resposta, 'Tamanho M para quem usa 1,60m.')
        self.assertIsNotNone(pergunta.respondida_em)
