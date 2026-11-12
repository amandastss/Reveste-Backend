from rest_framework.viewsets import ModelViewSet

from ..models import Seguidor
from ..serializers import SeguidorSerializer


class SeguidorViewSet(ModelViewSet):
    queryset = Seguidor.objects.all()
    serializer_class = SeguidorSerializer
