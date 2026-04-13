from rest_framework.serializers import ModelSerializer

from core.models import HistoricoPesquisa


class HistoricoPesquisaSerializer(ModelSerializer):
    class Meta:
        model = HistoricoPesquisa
        fields = '__all__'
