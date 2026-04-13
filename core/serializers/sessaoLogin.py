from rest_framework.serializers import ModelSerializer

from core.models import SessaoLogin


class SessaoLoginSerializer(ModelSerializer):
    class Meta:
        model = SessaoLogin
        fields = '__all__'
