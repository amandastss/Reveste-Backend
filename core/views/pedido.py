from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Pedido
from core.serializers import PedidoSerializer


class PedidoViewSet(ModelViewSet):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Pedido.objects.filter(
            usuario=self.request.user
        ).prefetch_related(
            'itens__produto'
        ).order_by('-data_pedido')

    def perform_create(self, serializer):
        serializer.save(
            usuario=self.request.user
        )
