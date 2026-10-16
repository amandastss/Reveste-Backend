from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from core.models import ImagemProduto, Produto


class ProductImageListField(serializers.ListField):
    child = serializers.ImageField()

    def to_representation(self, value):
        if not value:
            return []

        request = self.context.get('request')
        imagens = []

        for item in value:
            if hasattr(item, 'imagem') and item.imagem:
                arquivo = item.imagem.url
            elif getattr(item, 'imagem_url', None):
                arquivo = item.imagem_url
            else:
                arquivo = item

            if not arquivo:
                continue

            if request and not str(arquivo).startswith('http'):
                imagens.append(request.build_absolute_uri(arquivo))
            else:
                imagens.append(arquivo)

        return imagens


class ProdutoSerializer(ModelSerializer):
    imagem_url = SerializerMethodField(read_only=True)
    imagens = ProductImageListField(required=False)

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
            'imagens',
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

        extra_kwargs = {'imagem': {'required': False}}

    def get_imagem_url(self, obj):
        request = self.context.get('request')

        if obj.imagem:
            if request:
                return request.build_absolute_uri(obj.imagem.url)

            return obj.imagem.url

        return None

    def create(self, validated_data):
        imagens = validated_data.pop('imagens', [])
        produto = super().create(validated_data)

        if imagens:
            for imagem in imagens:
                ImagemProduto.objects.create(produto=produto, imagem=imagem)

            if not produto.imagem:
                produto.imagem = imagens[0]
                produto.save(update_fields=['imagem'])

        return produto

    def update(self, instance, validated_data):
        imagens = validated_data.pop('imagens', [])
        produto = super().update(instance, validated_data)

        if imagens:
            for imagem in imagens:
                ImagemProduto.objects.create(produto=produto, imagem=imagem)

            if not produto.imagem:
                produto.imagem = imagens[0]
                produto.save(update_fields=['imagem'])

        return produto
