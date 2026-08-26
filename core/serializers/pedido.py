from rest_framework import serializers

from core.models import ItemPedido, Pedido


class PedidoItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = ItemPedido

        fields = [
            'id',
            'produto',
            'quantidade',
            'preco',
            'nome',
            'cor',
            'tamanho',
            'imagem_url',
            'subtotal',
        ]

        read_only_fields = fields

    def get_subtotal(self, obj):
        return obj.preco * obj.quantidade


class PedidoSerializer(serializers.ModelSerializer):
    itens = PedidoItemSerializer(
        many=True,
        read_only=True
    )

    total = serializers.SerializerMethodField()

    class Meta:
        model = Pedido

        fields = [
            'id',
            'usuario',
            'data_pedido',
            'status',
            'itens',
            'total',
        ]

        read_only_fields = fields

    def get_total(self, obj):
        return sum(
            item.preco * item.quantidade
            for item in obj.itens.all()
        )
