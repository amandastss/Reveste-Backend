from django.db import models

from core.models.categoria import Categoria
from core.models.user import User
from uploader.models import Image


class Produto(models.Model):
    CONDICAO_CHOICES = [
        ('novo', 'Novo'),
        ('seminovo', 'Seminovo'),
        ('usado', 'Usado'),
    ]

    descricao = models.CharField(max_length=100)
    nome = models.CharField(max_length=60)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.CharField(max_length=60)
    condicao = models.CharField(
        max_length=10,
        choices=CONDICAO_CHOICES,
        default='novo'
    )

    imagem = models.ForeignKey(
        Image,
        related_name='+',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.nome
