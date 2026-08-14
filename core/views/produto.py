from rest_framework.viewsets import ModelViewSet

from ..models import Produto
from ..serializers import ProdutoSerializer


class ProdutoViewSet(ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer

    def get_serializer_context(self):
        return {'request': self.request}
