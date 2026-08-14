from django.conf import settings  # Importação correta para puxar o User
from django.db import models

from .categoria import Categoria


class Produto(models.Model):
    CONDICAO_CHOICES = [
        ('novo', 'Novo'),
        ('seminovo', 'Seminovo'),
        ('usado', 'Usado'),
    ]

    nome = models.CharField(max_length=60)
    # TextField é melhor para descrição de brechó, permite textos longos sem limite de 100 caracteres
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.CharField(max_length=60)
    condicao = models.CharField(max_length=10, choices=CONDICAO_CHOICES, default='novo')
    imagem = models.ImageField(upload_to='produtos/', null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True)

    # O vendedor é quem cadastra o produto. Obriguei a ter um vendedor e adicionei o related_name
    vendedor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='produtos_a_venda')

    def __str__(self):
        return self.nome
