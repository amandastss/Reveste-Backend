from django.conf import settings
from django.db import models

from .produto import Produto


class Compra(models.Model):
    class StatusCompra(models.IntegerChoices):
        CARRINHO = 1, 'Carrinho'
        REALIZADA = 2, 'Realizada'
        PAGA = 3, 'Paga'
        ENTREGUE = 4, 'Entregue'

    comprador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='minhas_compras')
    status = models.IntegerField(choices=StatusCompra.choices, default=StatusCompra.CARRINHO)

    data_compra = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Pedido {self.id} - Comprador: {self.comprador}'


class ItemCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.IntegerField(default=1)

    preco_item = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.quantidade}x {self.produto.nome} (Pedido {self.compra.id})'
