from rest_framework.viewsets import ModelViewSet

from core.models import Pedido
from core.serializers.pedido import PedidoCreateUpdateSerializer, PedidoListSerializer


class PedidoViewSet(ModelViewSet):
    queryset = Pedido.objects.all()

    def get_serializer_class(self):
        if self.action in {'list', 'retrieve'}:
            return PedidoListSerializer
        if self.action in {'create', 'update', 'partial_update'}:
            return PedidoCreateUpdateSerializer
        return PedidoListSerializer
