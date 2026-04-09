from django.db import models


class Venda(models.Model):
    pedido = models.ForeignKey(
        'core.Pedido',
        on_delete=models.
        CASCADE, related_name='vendas',
        null=True, blank=True
        )
    data_venda = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Venda do pedido {self.pedido.id}'
