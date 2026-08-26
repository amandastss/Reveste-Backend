from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import Produto
from core.serializers import ProdutoSerializer


class ProdutoViewSet(ModelViewSet):
    serializer_class = ProdutoSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Produto.objects.all().order_by('-criado_em')

        disponivel = self.request.query_params.get('disponivel')

        if disponivel is not None:
            queryset = queryset.filter(
                disponivel=disponivel.lower() == 'true'
            )

        categoria = self.request.query_params.get('categoria')

        if categoria:
            queryset = queryset.filter(
                categoria_id=categoria
            )

        return queryset

    def get_serializer_context(self):
        return {
            'request': self.request
        }

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        produto = self.get_object()

        if produto.user != request.user:
            return Response(
                {
                    'detail': 'Você não pode alterar um produto de outro vendedor.'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        produto = self.get_object()

        if produto.user != request.user:
            return Response(
                {
                    'detail': 'Você não pode excluir um produto de outro vendedor.'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        return super().destroy(request, *args, **kwargs)
