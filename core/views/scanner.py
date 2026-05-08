from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class ScannerViewSet(ViewSet):
    def create(self, request):
        imagem = request.FILES.get('foto')

        if not imagem:
            return Response({'erro': 'sem imagem'}, status=400)

        return Response({
            'nome': 'Produto IA',
            'marca': 'Marca IA',
            'preco': 123.45,
            'descricao': 'Gerado pela IA'
        })
