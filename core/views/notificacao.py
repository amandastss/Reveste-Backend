from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Notificacao
from core.serializers import NotificacaoSerializer


class NotificacaoViewSet(ModelViewSet):
    serializer_class = NotificacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notificacao.objects.filter(usuario=self.request.user).select_related('usuario', 'produto', 'pergunta')
