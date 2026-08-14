from rest_framework.viewsets import ModelViewSet

from ..models import Venda
from ..serializers import VendaSerializer


class VendaViewSet(ModelViewSet):
    queryset = Venda.objects.all()
    serializer_class = VendaSerializer
