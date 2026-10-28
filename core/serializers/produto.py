from rest_framework.serializers import ModelSerializer, SerializerMethodField
from core.models import Produto


class ProdutoSerializer(ModelSerializer):
    imagem_url = SerializerMethodField()

    class Meta:
        model = Produto
        fields = (
            'id', 'nome', 'descricao', 'preco', 'marca', 'condicao',
            'imagem', 'categoria', 'vendedor', 'disponivel', 'imagem_url',
        )
        read_only_fields = ('id', 'vendedor', 'disponivel')
        extra_kwargs = {'imagem': {'required': False}}

    def get_imagem_url(self, obj):
        request = self.context.get('request')
        if not obj.imagem:
            return None
        return request.build_absolute_uri(obj.imagem.url) if request else obj.imagem.url
