from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from core.models import Notificacao, Pergunta, Produto, User


class PerguntaAPITest(TestCase):
    def setUp(self):
        Notificacao.objects.all().delete()
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

    def test_pergunta_pode_ser_criada_sem_login(self):
        response = self.client.post(
            '/api/perguntas/',
            {'produto': self.produto.id, 'texto': 'A camiseta é de algodão orgânico?'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Pergunta.objects.filter(produto=self.produto, texto='A camiseta é de algodão orgânico?').exists()
        )

    def test_criar_pergunta_retorna_dados_do_usuario_que_perguntou(self):
        image = BytesIO()
        Image.new('RGB', (50, 50), color='red').save(image, format='PNG')
        image.seek(0)
        self.buyer.profile_image = SimpleUploadedFile('buyer.png', image.read(), content_type='image/png')
        self.buyer.save()

        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(
            '/api/perguntas/',
            {'produto': self.produto.id, 'texto': 'Essa camiseta é 100% algodão?'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn('usuario', response.data)
        self.assertEqual(response.data['user'], self.buyer.id)
        self.assertEqual(response.data['usuario']['id'], self.buyer.id)
        self.assertEqual(response.data['usuario']['name'], self.buyer.name)
        self.assertTrue(response.data['foto'])
        self.assertTrue(response.data['profile_image'])

    def test_notificacao_inclui_produto_pergunta_link_e_permite_marcar_como_lida(self):
        self.client.force_authenticate(user=self.buyer)
        created = self.client.post(
            '/api/perguntas/',
            {'produto': self.produto.id, 'texto': 'A camisa tem manga curta?'},
            format='json',
        )

        self.client.force_authenticate(user=self.seller)
        list_response = self.client.get('/api/notificacoes/')
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data['results']), 1)
        notification = list_response.data['results'][0]
        self.assertEqual(notification['usuario'], self.seller.id)
        self.assertEqual(notification['produto_id'], self.produto.id)
        self.assertEqual(notification['pergunta_id'], created.data['id'])
        self.assertIn(f'/produto/{self.produto.id}/perguntas?pergunta_id={created.data["id"]}', notification['link'])
        self.assertFalse(notification['lida'])

        patch_response = self.client.patch(
            f'/api/notificacoes/{notification["id"]}/',
            {'lida': True},
            format='json',
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertTrue(patch_response.data['lida'])

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
