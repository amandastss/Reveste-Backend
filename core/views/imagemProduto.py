from rest_framework.viewsets import ModelViewSet

from ..models import ImagemProduto
from ..serializers import ImagemProdutoSerializer


class ImagemProdutoViewSet(ModelViewSet):
    queryset = ImagemProduto.objects.all()
    serializer_class = ImagemProdutoSerializer
