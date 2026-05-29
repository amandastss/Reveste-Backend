from rest_framework.viewsets import ModelViewSet

from core.models import HistoricoPesquisa
from core.serializers import HistoricoPesquisaSerializer


class HistoricoPesquisaViewSet(ModelViewSet):
    serializer_class = HistoricoPesquisaSerializer

    def get_queryset(self):
        return HistoricoPesquisa.objects.filter(
            usuario=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)