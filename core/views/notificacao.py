from rest_framework.viewsets import ModelViewSet

from ..models import Notificacao
from ..serializers import NotificacaoSerializer


class NotificacaoViewSet(ModelViewSet):
    queryset = Notificacao.objects.all()
    serializer_class = NotificacaoSerializer
