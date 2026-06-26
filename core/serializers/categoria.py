from rest_framework import serializers

from core.models import Categoria


class CategoriaSerializer(serializers.ModelSerializer):
    imagem_url = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = ['id', 'nome', 'imagem_url']

    def get_imagem_url(self, obj):
        request = self.context.get('request')
        if obj.imagem and obj.imagem.file:
            url = obj.imagem.file.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None
