from django.db import models


class SessaoLogin(models.Model):
    usuario = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='sessoes'
    )
    token = models.CharField(max_length=255)
    data_login = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_login']

    def __str__(self):
        return f"Sessão de {self.usuario}"
