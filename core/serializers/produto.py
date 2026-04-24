from rest_framework.serializers import ModelSerializer, SlugRelatedField

from core.models import Produto
from uploader.models import Image
from uploader.serializers import ImageSerializer


class ProdutoSerializer(ModelSerializer):
    imagem_attachment_key = SlugRelatedField(
        source='imagem',
        queryset=Image.objects.all(),
        slug_field='attachment_key',
        write_only=True,
        required=False
    )

    imagem = ImageSerializer(read_only=True)

    class Meta:
        model = Produto
        fields = '__all__'
