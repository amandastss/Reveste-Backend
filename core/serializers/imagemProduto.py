from rest_framework.serializers import ModelSerializer

from core.models import ImagemProduto


class ImagemProdutoSerializer(ModelSerializer):
    class Meta:
        model = ImagemProduto
        fields = '__all__'
