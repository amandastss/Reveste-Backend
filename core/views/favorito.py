from rest_framework.viewsets import ModelViewSet

from ..models import Favorito
from ..serializers import FavoritoSerializer


class FavoritoViewSet(ModelViewSet):
    queryset = Favorito.objects.all()
    serializer_class = FavoritoSerializer
