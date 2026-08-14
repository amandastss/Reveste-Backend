from rest_framework import serializers

from core.models import Compra, ItemCompra


class ItemCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCompra
        fields = ('id', 'produto', 'quantidade', 'preco_item')
        read_only_fields = ('preco_item',)


class CompraSerializer(serializers.ModelSerializer):
    comprador = serializers.HiddenField(default=serializers.CurrentUserDefault())

    itens = ItemCompraSerializer(many=True)

    class Meta:
        model = Compra
        fields = ('id', 'comprador', 'status', 'data_compra', 'itens')

    def create(self, validated_data):
        itens_data = validated_data.pop('itens')
        compra = Compra.objects.create(**validated_data)

        for item in itens_data:
            produto_obj = item['produto']
            quantidade = item['quantidade']
            preco_item = produto_obj.preco

            ItemCompra.objects.create(compra=compra, produto=produto_obj, quantidade=quantidade, preco_item=preco_item)

        return compra
