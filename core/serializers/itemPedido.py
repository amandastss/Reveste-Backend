from rest_framework import serializers

from core.models import ItemPedido


class ItemPedidoSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = ItemPedido

        fields = [
            'id',
            'pedido',
            'produto',
            'quantidade',
            'preco',
            'nome',
            'cor',
            'tamanho',
            'imagem_url',
            'subtotal',
        ]

        read_only_fields = [
            'id',
            'pedido',
            'produto',
            'preco',
            'nome',
            'imagem_url',
            'subtotal',
        ]

    def get_subtotal(self, obj):
        return obj.preco * obj.quantidade
