from rest_framework import serializers

from core.models import Venda


class VendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venda

        fields = [
            'id',
            'pedido',
            'vendedor',
            'data_venda',
        ]

        read_only_fields = fields
