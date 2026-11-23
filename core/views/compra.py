from rest_framework import viewsets

from ..models import Compra
from ..serializers.compra import CompraSerializer


class CompraViewSet(viewsets.ModelViewSet):
    serializer_class = CompraSerializer

    def get_queryset(self):
        usuario = self.request.user
        if usuario.is_superuser:
            return Compra.objects.all()
        return Compra.objects.filter(comprador=usuario)
