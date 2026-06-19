from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import Pedido, ItemPedido, Produto
from core.serializers import ItemPedidoSerializer


class CarrinhoView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        pedido, _ = Pedido.objects.get_or_create(usuario=request.user, status='PENDENTE')
        itens = pedido.itens.all()
        serializer = ItemPedidoSerializer(itens, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Espera payload: productId, name, color, size, price, quantity, image
        data = request.data
        product_id = data.get('productId')
        quantity = data.get('quantity', 1)
        price = data.get('price') or data.get('price')

        if not product_id:
            return Response({'detail': 'productId é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            produto = Produto.objects.get(id=product_id)
        except Produto.DoesNotExist:
            return Response({'detail': 'Produto não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        pedido, _ = Pedido.objects.get_or_create(usuario=request.user, status='PENDENTE')

        # Tentar localizar item existente do mesmo produto (ignora variações por simplicidade)
        item_qs = ItemPedido.objects.filter(pedido=pedido, produto=produto)
        if item_qs.exists():
            item = item_qs.first()
            item.quantidade = item.quantidade + int(quantity)
            item.preco = price or item.preco
        else:
            item = ItemPedido(
                pedido=pedido,
                produto=produto,
                quantidade=int(quantity),
                preco=price or produto.preco,
                nome=data.get('name'),
                cor=data.get('color'),
                tamanho=data.get('size'),
                imagem_url=data.get('image'),
            )

        item.save()
        serializer = ItemPedidoSerializer(item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
