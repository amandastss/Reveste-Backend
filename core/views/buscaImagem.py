from rest_framework.viewsets import ModelViewSet

from core.models import BuscaImagem
from core.serializers import BuscaImagemSerializer


class BuscaImagemViewSet(ModelViewSet):
    queryset = BuscaImagem.objects.all()
    serializer_class = BuscaImagemSerializer
