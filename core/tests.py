from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from core.models import Produto
from core.models.user import User
from core.serializers import ProdutoSerializer


class ProdutoSerializerMultipleImagesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='vendedor@teste.com',
            password='senha123',
            name='Vendedor Teste',
            role='seller',
        )

    def _create_image(self, name):
        image_file = BytesIO()
        image = Image.new('RGB', (100, 100), color='blue')
        image.save(image_file, format='PNG')
        image_file.seek(0)
        return SimpleUploadedFile(name, image_file.read(), content_type='image/png')

    def test_product_allows_multiple_images(self):
        image_1 = self._create_image('imagem_1.png')
        image_2 = self._create_image('imagem_2.png')

        serializer = ProdutoSerializer(
            data={
                'descricao': 'Produto de teste',
                'nome': 'Camiseta',
                'preco': '89.90',
                'marca': 'Reveste',
                'condicao': 'novo',
                'imagens': [image_1, image_2],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        produto = serializer.save(user=self.user)

        self.assertEqual(produto.imagens.count(), 2)
        self.assertTrue(produto.imagem)
        self.assertIn('imagem_1', produto.imagem.name)


class ProdutoApiListTests(TestCase):
    def test_list_products_without_images(self):
        user = User.objects.create_user(
            email='lista@teste.com',
            password='senha123',
            name='Vendedor',
        )
        Produto.objects.create(
            descricao='Produto de teste',
            nome='Camiseta',
            preco='89.90',
            marca='Reveste',
            user=user,
        )

        response = APIClient().get('/api/produtos/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['imagens'], [])
