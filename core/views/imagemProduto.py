from rest_framework.viewsets import ModelViewSet

from core.models import ImagemProduto
from core.serializers import ImagemProdutoSerializer


class ImagemProdutoViewSet(ModelViewSet):
    queryset = ImagemProduto.objects.all()
    serializer_class = ImagemProdutoSerializer
