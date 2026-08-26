from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import ItemPedido, Pedido, Produto, Venda
from core.serializers import ItemPedidoSerializer


class CarrinhoView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        pedido, _ = Pedido.objects.get_or_create(
            usuario=request.user,
            status='PENDENTE'
        )

        itens = pedido.itens.select_related('produto').all()

        serializer = ItemPedidoSerializer(
            itens,
            many=True,
            context={'request': request}
        )

        total = sum(
            item.preco * item.quantidade
            for item in itens
        )

        return Response({
            'pedido_id': pedido.id,
            'status': pedido.status,
            'itens': serializer.data,
            'total': total,
        })

    def post(self, request):
        product_id = request.data.get('productId')
        quantity = request.data.get('quantity', 1)

        if not product_id:
            return Response(
                {
                    'detail': 'productId é obrigatório.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {
                    'detail': 'quantity deve ser um número inteiro.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {
                    'detail': 'quantity deve ser maior que zero.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            produto = Produto.objects.get(
                id=product_id,
                disponivel=True
            )
        except Produto.DoesNotExist:
            return Response(
                {
                    'detail': 'Produto não encontrado ou indisponível.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        pedido, _ = Pedido.objects.get_or_create(
            usuario=request.user,
            status='PENDENTE'
        )

        item, created = ItemPedido.objects.get_or_create(
            pedido=pedido,
            produto=produto,
            defaults={
                'quantidade': quantity,
                'preco': produto.preco,
                'nome': produto.nome,
                'imagem_url': (
                    request.build_absolute_uri(produto.imagem.url)
                    if produto.imagem
                    else None
                ),
            }
        )

        if not created:
            item.quantidade += quantity
            item.save()

        serializer = ItemPedidoSerializer(
            item,
            context={'request': request}
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    def delete(self, request):
        product_id = request.data.get('productId')

        if not product_id:
            return Response(
                {
                    'detail': 'productId é obrigatório.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        pedido = Pedido.objects.filter(
            usuario=request.user,
            status='PENDENTE'
        ).first()

        if not pedido:
            return Response(
                {
                    'detail': 'Carrinho vazio.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        item = pedido.itens.filter(
            produto_id=product_id
        ).first()

        if not item:
            return Response(
                {
                    'detail': 'Produto não está no carrinho.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        item.delete()

        return Response(
            {
                'detail': 'Produto removido do carrinho.'
            },
            status=status.HTTP_204_NO_CONTENT
        )


class FinalizarCompraView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        pedido = Pedido.objects.select_for_update().filter(
            usuario=request.user,
            status='PENDENTE'
        ).first()

        if not pedido:
            return Response(
                {
                    'detail': 'Nenhum pedido pendente encontrado.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        itens = list(
            pedido.itens.select_related('produto').all()
        )

        if not itens:
            return Response(
                {
                    'detail': 'O carrinho está vazio.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Mapeia os vendedores dos itens do carrinho
        vendedores = {
            item.produto.user
            for item in itens
        }

        # 2. Verifica se há mais de um vendedor (o que quebra a regra da sua API)
        if len(vendedores) > 1:
            return Response(
                {
                    'detail': (
                        'Todos os produtos do carrinho devem '
                        'pertencer ao mesmo vendedor.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        for item in itens:
            produto = Produto.objects.select_for_update().get(
                id=item.produto_id
            )

            if not produto.disponivel:
                return Response(
                    {
                        'detail': (
                            f'O produto "{produto.nome}" '
                            'não está mais disponível.'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if produto.user == request.user:
                return Response(
                    {
                        'detail': (
                            'Você não pode comprar seu próprio produto.'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        for item in itens:
            produto = item.produto

            item.preco = produto.preco
            item.nome = produto.nome

            if produto.imagem:
                item.imagem_url = request.build_absolute_uri(
                    produto.imagem.url
                )

            item.save()

            produto.disponivel = False
            produto.save(update_fields=['disponivel'])

        # 3. Finaliza o status do pedido
        pedido.status = 'PAGO'
        pedido.save(update_fields=['status'])

        # 4. Pega o único vendedor daquele "Set" e cria a Venda
        vendedor = vendedores.pop()

        Venda.objects.get_or_create(
            pedido=pedido,
            vendedor=vendedor
        )

        return Response(
            {
                'detail': 'Compra realizada com sucesso.',
                'pedido_id': pedido.id,
                'status': pedido.status,
            },
            status=status.HTTP_200_OK
        )
