from django.db import models


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

    def __str__(self):
        return self.nome
