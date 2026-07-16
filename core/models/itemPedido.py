from django.db import models

from core.models.pedido import Pedido
from core.models.produto import Produto


class ItemPedido(models.Model):

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='+')

    quantidade = models.IntegerField(default=1)

    def __str__(self):
        return f'{self.quantidade}x do Produto {self.produto.id} (Pedido {self.pedido.id})'
