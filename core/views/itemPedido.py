from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.models import ItemPedido
from core.serializers import ItemPedidoSerializer


class ItemPedidoViewSet(ReadOnlyModelViewSet):
    """Expõe os itens somente para consulta e apenas ao dono do pedido."""

    serializer_class = ItemPedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ItemPedido.objects
            .filter(pedido__usuario=self.request.user)
            .select_related('pedido', 'produto')
            .order_by('id')
        )
