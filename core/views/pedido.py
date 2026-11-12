from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from ..models import Pedido
from ..serializers.pedido import PedidoSerializer


class PedidoViewSet(ReadOnlyModelViewSet):
    """Lista apenas pedidos do usuario autenticado.

    O carrinho e o fluxo de pagamento controlam criacao e mudancas de status.
    """

    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Pedido.objects
            .filter(usuario=self.request.user)
            .prefetch_related('itens__produto')
            .order_by('-criado_em')
        )
