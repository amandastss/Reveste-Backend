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
    # Campos opcionais para armazenar snapshot do produto no carrinho
    nome = models.CharField(max_length=120, null=True, blank=True)
    cor = models.CharField(max_length=60, null=True, blank=True)
    tamanho = models.CharField(max_length=30, null=True, blank=True)
    imagem_url = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return f"{self.quantidade}x {self.produto} (Pedido {self.pedido.id})"
