from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Pergunta(models.Model):
    produto = models.ForeignKey(
        'Produto',
        on_delete=models.CASCADE,
        related_name='perguntas'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='perguntas_feitas'
    )
    texto = models.TextField()
    resposta = models.TextField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    respondida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.user} - {self.produto}'
