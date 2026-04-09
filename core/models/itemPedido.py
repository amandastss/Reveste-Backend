from django.db import models


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        'core.Pedido',
        on_delete=models.CASCADE,
        related_name='itens'
    )
    produto = models.ForeignKey(
        'core.Produto',
        on_delete=models.CASCADE,
        related_name='itens_pedido'
    )
    quantidade = models.PositiveIntegerField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantidade}x {self.produto} (Pedido {self.pedido.id})"
