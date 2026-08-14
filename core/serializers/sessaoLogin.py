from rest_framework import serializers

from ..models.sessaoLogin import SessaoLogin


class SessaoLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessaoLogin
        fields = '__all__'
