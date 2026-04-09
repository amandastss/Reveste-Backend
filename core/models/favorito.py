from django.db import models


class Favorito(models.Model):
    usuario = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='favoritos'
    )
    produto = models.ForeignKey(
        'core.Produto',
        on_delete=models.CASCADE,
        related_name='favoritado_por'
    )

    class Meta:
        unique_together = ('usuario', 'produto')

    def __str__(self):
        return f"{self.usuario} favoritou {self.produto}"
