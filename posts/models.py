from django.db import models

from uploader.models import Image


class Post(models.Model):
    title = models.CharField(max_length=255)
    image = models.ForeignKey(
        Image,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.title
