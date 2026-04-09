from django.conf import settings
from django.db import models

from core.models.produto import Produto


class BuscaImagem(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, null=True, blank=True)
    imagem = models.CharField(max_length=255)
    data_busca = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario} - {self.data_busca}"
