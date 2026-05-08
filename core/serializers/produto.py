from rest_framework.serializers import ModelSerializer

from core.models import Produto


class ProdutoSerializer(ModelSerializer):
    class Meta:
        model = Produto
        fields = '__all__'
        extra_kwargs = {
            'imagem': {'required': False}
        }

    def create(self, validated_data):
        imagem_url = validated_data.get('imagem')

        if imagem_url:
            if 'media/' in imagem_url:
                caminho = imagem_url.split('media/')[1]
                validated_data['imagem'] = caminho

        print(validated_data)
        return super().create(validated_data)
