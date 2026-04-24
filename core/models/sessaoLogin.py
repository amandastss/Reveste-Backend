from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class SessaoLogin(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255)
