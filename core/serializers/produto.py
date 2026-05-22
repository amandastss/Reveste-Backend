from rest_framework.serializers import ModelSerializer, SerializerMethodField

from core.models import Produto


class ProdutoSerializer(ModelSerializer):
    imagem_url = SerializerMethodField()

    class Meta:
        model = Produto
        fields = '__all__'
        extra_kwargs = {
            'imagem': {'required': False}
        }

    def get_imagem_url(self, obj):
        request = self.context.get('request')

        if obj.imagem:
            return request.build_absolute_uri(obj.imagem.url)

        return None
