from django.db import models


class Pedido(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('ENVIADO', 'Enviado'),
        ('CANCELADO', 'Cancelado'),
    ]

    # Relacionamento com o Usuário
    usuario = models.ForeignKey('core.User', on_delete=models.PROTECT, related_name='pedidos')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Pedido {self.id} - {self.usuario.email}'
