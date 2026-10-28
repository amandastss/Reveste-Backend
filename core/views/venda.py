from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from ..models import Venda
from ..serializers import VendaSerializer


class VendaViewSet(ReadOnlyModelViewSet):
    serializer_class = VendaSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Venda.objects.filter(
            Q(vendedor=user) | Q(pedido__usuario=user),
        ).distinct().select_related('vendedor', 'pedido')
