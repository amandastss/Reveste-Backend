from django.core.exceptions import ValidationError
from django.db import models


class Seguidor(models.Model):
    usuario = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='seguindo'
    )
    seguindo = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='seguidores'
    )

    class Meta:
        unique_together = ('usuario', 'seguindo')

    def clean(self):
        if self.usuario == self.seguindo:
            raise ValidationError("Usuário não pode seguir a si mesmo.")

    def __str__(self):
        return f"{self.usuario} segue {self.seguindo}"
