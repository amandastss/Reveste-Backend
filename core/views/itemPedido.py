from rest_framework.viewsets import ModelViewSet

from ..models.itemPedido import ItemPedido
from ..serializers import ItemPedidoCreateUpdateSerializer, ItemPedidoListSerializer


class ItemPedidoViewSet(ModelViewSet):
    queryset = ItemPedido.objects.all()

    def get_serializer_class(self):
        if self.action in {'list', 'retrieve'}:
            return ItemPedidoListSerializer
        return ItemPedidoCreateUpdateSerializer
