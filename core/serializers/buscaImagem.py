from rest_framework.serializers import ModelSerializer

from core.models import BuscaImagem


class BuscaImagemSerializer(ModelSerializer):
    class Meta:
        model = BuscaImagem
        fields = '__all__'
