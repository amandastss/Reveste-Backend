from django.db import models
from .pedido import Pedido
from .produto import Produto

class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='+')
    quantidade = models.PositiveIntegerField(default=1)
    preco = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    nome = models.CharField(max_length=120, null=True, blank=True)
    cor = models.CharField(max_length=60, null=True, blank=True)
    tamanho = models.CharField(max_length=30, null=True, blank=True)
    imagem_url = models.CharField(max_length=500, null=True, blank=True)

    @property
    def subtotal(self):
        return (self.preco if self.preco is not None else self.produto.preco) * self.quantidade

    def __str__(self):
        return f'{self.quantidade}x do Produto {self.produto_id} (Pedido {self.pedido_id})'
