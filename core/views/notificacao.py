from rest_framework.viewsets import ModelViewSet

from core.models import Notificacao
from core.serializers import NotificacaoSerializer


class NotificacaoViewSet(ModelViewSet):
    queryset = Notificacao.objects.all()
    serializer_class = NotificacaoSerializer
