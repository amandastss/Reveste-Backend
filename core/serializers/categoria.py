from rest_framework import serializers

from core.models import Categoria


class CategoriaSerializer(serializers.ModelSerializer):
    imagem_url = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = ['id', 'nome', 'imagem_url']

    def get_imagem_url(self, obj):
        if obj.imagem and obj.imagem.file:
            return obj.imagem.file.url
        return None
