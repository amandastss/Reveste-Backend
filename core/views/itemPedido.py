from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from ..models.itemPedido import ItemPedido
from ..serializers import ItemPedidoListSerializer


class ItemPedidoViewSet(ReadOnlyModelViewSet):
    serializer_class = ItemPedidoListSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ItemPedido.objects.filter(
            pedido__usuario=self.request.user,
        ).select_related('pedido', 'produto')
