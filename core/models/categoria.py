from django.db import models

from uploader.models import Image


class Categoria(models.Model):
    nome = models.CharField(max_length=50)

    imagem = models.ForeignKey(
        Image,
        related_name='+',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        return self.nome
