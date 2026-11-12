from django.db import models


class Notificacao(models.Model):
    usuario = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='notificacoes')
    produto = models.ForeignKey(
        'core.Produto',
        on_delete=models.CASCADE,
        related_name='notificacoes',
        null=True,
        blank=True,
    )
    pergunta = models.ForeignKey(
        'core.Pergunta',
        on_delete=models.CASCADE,
        related_name='notificacoes',
        null=True,
        blank=True,
    )
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    data_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_envio']

    @property
    def link(self):
        if not self.produto_id or not self.pergunta_id:
            return None
        return f'/produto/{self.produto_id}/perguntas?pergunta_id={self.pergunta_id}'

    def __str__(self):
        return f'Notificação para {self.usuario}'
