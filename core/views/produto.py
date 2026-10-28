from rest_framework.permissions import BasePermission, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet
from ..models import Produto
from ..serializers import ProdutoSerializer


class IsVendedorDoProduto(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.is_authenticated and obj.vendedor_id == request.user.id


class ProdutoViewSet(ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, IsVendedorDoProduto)

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        serializer.save(vendedor=self.request.user)
