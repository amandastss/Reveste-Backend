from django.conf import settings
from django.db import models
from .categoria import Categoria

class Produto(models.Model):
    CONDICAO_CHOICES = [('novo','Novo'),('seminovo','Seminovo'),('usado','Usado')]
    nome = models.CharField(max_length=60)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.CharField(max_length=60)
    condicao = models.CharField(max_length=10, choices=CONDICAO_CHOICES, default='novo')
    imagem = models.ImageField(upload_to='produtos/', null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True)
    vendedor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='produtos_a_venda')
    disponivel = models.BooleanField(default=True)
    reserva_pedido = models.ForeignKey('core.Pedido', on_delete=models.SET_NULL, null=True, blank=True, related_name='produtos_reservados')
    reservado_ate = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nome
