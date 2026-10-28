from rest_framework.serializers import ModelSerializer, SerializerMethodField
from ..models.itemPedido import ItemPedido

class ItemPedidoListSerializer(ModelSerializer):
    produto_nome = SerializerMethodField()
    total = SerializerMethodField()
    class Meta:
        model = ItemPedido
        fields = ('id','produto','produto_nome','quantidade','preco','nome','cor','tamanho','imagem_url','total')
    def get_produto_nome(self, instance):
        return instance.nome or instance.produto.nome
    def get_total(self, instance):
        return instance.subtotal

class ItemPedidoCreateUpdateSerializer(ModelSerializer):
    class Meta:
        model = ItemPedido
        fields = ('id','produto','quantidade','preco','nome','cor','tamanho','imagem_url')
        read_only_fields = ('preco','nome','cor','tamanho','imagem_url')
