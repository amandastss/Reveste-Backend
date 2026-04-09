from rest_framework.viewsets import ModelViewSet

from core.models import Venda
from core.serializers import VendaSerializer


class VendaViewSet(ModelViewSet):
    queryset = Venda.objects.all()
    serializer_class = VendaSerializer
