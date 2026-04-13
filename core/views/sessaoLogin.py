from rest_framework.viewsets import ModelViewSet

from core.models import SessaoLogin
from core.serializers import SessaoLoginSerializer


class SessaoLoginViewSet(ModelViewSet):
    queryset = SessaoLogin.objects.all()
    serializer_class = SessaoLoginSerializer
