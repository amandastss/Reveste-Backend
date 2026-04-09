from rest_framework.serializers import ModelSerializer

from core.models import ItemPedido


class ItemPedidoSerializer(ModelSerializer):
    class Meta:
        model = ItemPedido
        fields = '__all__'
