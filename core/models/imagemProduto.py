from django.db import models


class ImagemProduto(models.Model):
    produto = models.ForeignKey('core.Produto', on_delete=models.CASCADE, related_name='imagens')
    busca_imagem = models.ForeignKey('core.BuscaImagem', on_delete=models.SET_NULL, null=True, blank=True)
    imagem = models.ImageField(upload_to='produtos/', null=True, blank=True)
    imagem_url = models.CharField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.imagem and not self.imagem_url:
            self.imagem_url = self.imagem.url

        super().save(*args, **kwargs)

    def __str__(self):
        return f'Imagem de {self.produto.nome}'
