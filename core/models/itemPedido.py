from django.db import models


class ItemPedido(models.Model):

    pedido = models.ForeignKey(
        'core.Pedido',
        on_delete=models.CASCADE,
        related_name='itens'
    )

    produto = models.ForeignKey(
        'core.Produto',
        on_delete=models.PROTECT,
        related_name='itens_pedido'
    )

    # Em um brechó cada produto representa uma peça única
    quantidade = models.PositiveIntegerField(
        default=1
    )

    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    nome = models.CharField(
        max_length=120,
        null=True,
        blank=True
    )

    cor = models.CharField(
        max_length=60,
        null=True,
        blank=True
    )

    tamanho = models.CharField(
        max_length=30,
        null=True,
        blank=True
    )

    imagem_url = models.CharField(
        max_length=300,
        null=True,
        blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['pedido', 'produto'],
                name='produto_unico_por_pedido'
            )
        ]

    def save(self, *args, **kwargs):
        self.quantidade = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f'1x {self.produto} '
            f'(Pedido {self.pedido.id})'
        )

    @property
    def subtotal(self):
        return self.preco
