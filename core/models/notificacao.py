from django.db import models


class Notificacao(models.Model):
    usuario = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='notificacoes'
    )
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    data_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_envio']

    def __str__(self):
        return f"Notificação para {self.usuario}"
