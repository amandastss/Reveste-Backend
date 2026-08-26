from rest_framework.serializers import ModelSerializer, SerializerMethodField

from core.models import Produto


class ProdutoSerializer(ModelSerializer):
    imagem_url = SerializerMethodField(read_only=True)

    class Meta:
        model = Produto

        fields = [
            'id',
            'descricao',
            'nome',
            'preco',
            'marca',
            'condicao',
            'imagem',
            'imagem_url',
            'categoria',
            'user',
            'disponivel',
            'criado_em',
        ]

        read_only_fields = [
            'id',
            'user',
            'disponivel',
            'criado_em',
            'imagem_url',
        ]

        extra_kwargs = {
            'imagem': {
                'required': False
            }
        }

    def get_imagem_url(self, obj):
        request = self.context.get('request')

        if obj.imagem:
            if request:
                return request.build_absolute_uri(obj.imagem.url)

            return obj.imagem.url

        return None