from rest_framework.viewsets import ModelViewSet

from core.models import ItemPedido
from core.serializers import ItemPedidoSerializer


class ItemPedidoViewSet(ModelViewSet):
    queryset = ItemPedido.objects.all()
    serializer_class = ItemPedidoSerializer
