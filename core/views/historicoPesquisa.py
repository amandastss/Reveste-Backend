from rest_framework.viewsets import ModelViewSet

from core.models import HistoricoPesquisa
from core.serializers import HistoricoPesquisaSerializer


class HistoricoPesquisaViewSet(ModelViewSet):
    queryset = HistoricoPesquisa.objects.all()
    serializer_class = HistoricoPesquisaSerializer
