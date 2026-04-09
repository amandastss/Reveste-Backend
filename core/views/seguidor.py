from rest_framework.viewsets import ModelViewSet

from core.models import Seguidor
from core.serializers import SeguidorSerializer


class SeguidorViewSet(ModelViewSet):
    queryset = Seguidor.objects.all()
    serializer_class = SeguidorSerializer
