from rest_framework.serializers import CharField, ModelSerializer, SerializerMethodField

from ..models.itemPedido import ItemPedido


class ItemPedidoListSerializer(ModelSerializer):
    produto_nome = CharField(source='produto.nome', read_only=True)
    total = SerializerMethodField()

    class Meta:
        model = ItemPedido
        fields = ('id', 'produto_nome', 'quantidade', 'total')
        depth = 1

    def get_total(self, instance):
        return instance.quantidade * instance.produto.preco


class ItemPedidoCreateUpdateSerializer(ModelSerializer):
    class Meta:
        model = ItemPedido
        fields = ('id', 'produto', 'quantidade')
