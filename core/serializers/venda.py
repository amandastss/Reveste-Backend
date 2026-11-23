from rest_framework import serializers

from core.models import Venda
from .pedido import PedidoItemSerializer


class VendaSerializer(serializers.ModelSerializer):
    endereco_entrega = serializers.JSONField(source='pedido.endereco_entrega', read_only=True)
    status_entrega = serializers.CharField(source='pedido.status_entrega', read_only=True)
    itens = PedidoItemSerializer(source='pedido.itens', many=True, read_only=True)

    class Meta:
        model = Venda
        fields = [
            'id',
            'pedido',
            'vendedor',
            'data_venda',
            'endereco_entrega',
            'status_entrega',
            'itens',
        ]
        read_only_fields = fields
