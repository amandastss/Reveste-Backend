from rest_framework.serializers import ModelSerializer

from core.models import Notificacao


class NotificacaoSerializer(ModelSerializer):
    class Meta:
        model = Notificacao
        fields = '__all__'
