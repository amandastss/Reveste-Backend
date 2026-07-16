from rest_framework.serializers import (
    CharField,
    CurrentUserDefault,
    HiddenField,
    ModelSerializer,
    SerializerMethodField,
)

from core.models import ItemPedido, Pedido
from core.serializers.itemPedido import ItemPedidoCreateUpdateSerializer, ItemPedidoListSerializer


class PedidoCreateUpdateSerializer(ModelSerializer):
    usuario = HiddenField(default=CurrentUserDefault())
    itens = ItemPedidoCreateUpdateSerializer(many=True)

    class Meta:
        model = Pedido
        fields = ('id', 'usuario', 'status', 'itens')

    def create(self, validated_data):
        itens_data = validated_data.pop('itens')
        pedido = Pedido.objects.create(**validated_data)
        for item_data in itens_data:
            ItemPedido.objects.create(pedido=pedido, **item_data)
        return pedido

    def update(self, instance, validated_data):
        itens_data = validated_data.pop('itens', [])
        if itens_data:
            instance.itens.all().delete()
            for item_data in itens_data:
                ItemPedido.objects.create(pedido=instance, **item_data)
        return super().update(instance, validated_data)


class PedidoListSerializer(ModelSerializer):
    usuario = CharField(source='usuario.email', read_only=True)
    itens = ItemPedidoListSerializer(many=True, read_only=True)
    total_pedido = SerializerMethodField()

    class Meta:
        model = Pedido
        fields = ('id', 'usuario', 'status', 'criado_em', 'total_pedido', 'itens')

    def get_total_pedido(self, instance):
        return sum([item.quantidade * item.produto.preco for item in instance.itens.all()])


PedidoSerializer = PedidoListSerializer
ItemPedidoSerializer = ItemPedidoListSerializer
