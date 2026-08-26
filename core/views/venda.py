from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.models import Venda
from core.serializers import VendaSerializer


class VendaViewSet(ReadOnlyModelViewSet):
    serializer_class = VendaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Venda.objects.filter(
            vendedor=self.request.user
        ).select_related(
            'pedido',
            'vendedor'
        )
