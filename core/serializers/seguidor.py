from rest_framework.serializers import ModelSerializer

from core.models import Seguidor


class SeguidorSerializer(ModelSerializer):
    class Meta:
        model = Seguidor
        fields = '__all__'
