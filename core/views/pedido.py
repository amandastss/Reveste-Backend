from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet
from ..models import Pedido
from ..serializers.pedido import PedidoListSerializer

class PedidoViewSet(ReadOnlyModelViewSet):
    serializer_class = PedidoListSerializer
    permission_classes = (IsAuthenticated,)
    def get_queryset(self):
        return Pedido.objects.filter(usuario=self.request.user).prefetch_related('itens__produto')
