from django.db import models


class HistoricoPesquisa(models.Model):
    usuario = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='historico_pesquisa'
    )
    termo = models.CharField(max_length=100)
    data_pesquisa = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_pesquisa']

    def __str__(self):
        return f"{self.usuario} buscou '{self.termo}'"
