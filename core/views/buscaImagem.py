from rest_framework.viewsets import ModelViewSet

from ..models import BuscaImagem
from ..serializers import BuscaImagemSerializer


class BuscaImagemViewSet(ModelViewSet):
    queryset = BuscaImagem.objects.all()
    serializer_class = BuscaImagemSerializer
