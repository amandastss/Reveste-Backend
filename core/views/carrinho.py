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

        itens = pedido.itens.select_related(
            'produto'
        ).all()

        serializer = ItemPedidoSerializer(
            itens,
            many=True,
            context={'request': request}
        )

        total = sum(
            item.preco
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

        if not product_id:
            return Response(
                {
                    'detail': 'productId é obrigatório.'
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
                    'detail': (
                        'Produto não encontrado ou '
                        'não está mais disponível.'
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if produto.user == request.user:
            return Response(
                {
                    'detail': (
                        'Você não pode adicionar '
                        'seu próprio produto ao carrinho.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        pedido, _ = Pedido.objects.get_or_create(
            usuario=request.user,
            status='PENDENTE'
        )

        # Não permite adicionar a mesma peça duas vezes
        if pedido.itens.filter(
            produto=produto
        ).exists():
            return Response(
                {
                    'detail': (
                        'Este produto já está '
                        'no seu carrinho.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mantém a regra de um vendedor por pedido
        primeiro_item = pedido.itens.select_related(
            'produto__user'
        ).first()

        if primeiro_item:
            vendedor_atual = primeiro_item.produto.user

            if produto.user != vendedor_atual:
                return Response(
                    {
                        'detail': (
                            'Seu carrinho já possui produtos '
                            'de outro vendedor. Finalize ou '
                            'esvazie o carrinho antes de adicionar '
                            'produtos deste vendedor.'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        item = ItemPedido.objects.create(
            pedido=pedido,
            produto=produto,
            quantidade=1,
            preco=produto.preco,
            nome=produto.nome,
            imagem_url=(
                request.build_absolute_uri(
                    produto.imagem.url
                )
                if produto.imagem
                else None
            ),
        )

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
                    'detail': (
                        'Produto não está no carrinho.'
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        item.delete()

        return Response(
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
                    'detail': (
                        'Nenhum pedido pendente encontrado.'
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        itens = list(
            pedido.itens.select_related(
                'produto__user'
            ).all()
        )

        if not itens:
            return Response(
                {
                    'detail': 'O carrinho está vazio.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        vendedores = set()
        erro_validacao = None

        for item in itens:

            produto = Produto.objects.select_for_update().get(
                id=item.produto_id
            )

            # Verifica novamente se a peça ainda está disponível
            if not produto.disponivel:
                erro_validacao = f'O produto "{produto.nome}" não está mais disponível.'
                break

            # Impede comprar a própria peça
            if produto.user == request.user:
                erro_validacao = 'Você não pode comprar seu próprio produto.'
                break

            # Garante que cada peça tenha quantidade 1
            if item.quantidade != 1:
                erro_validacao = 'Produtos do brechó possuem apenas uma unidade disponível.'
                break

            vendedores.add(produto.user)

        if erro_validacao:
            return Response(
                {
                    'detail': erro_validacao
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Um pedido possui apenas um vendedor
        if len(vendedores) != 1:
            return Response(
                {
                    'detail': (
                        'Todos os produtos do carrinho '
                        'devem pertencer ao mesmo vendedor.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        vendedor = vendedores.pop()

        for item in itens:

            produto = Produto.objects.select_for_update().get(
                id=item.produto_id
            )

            # Atualiza as informações salvas no pedido
            item.preco = produto.preco
            item.nome = produto.nome
            item.quantidade = 1

            if produto.imagem:
                item.imagem_url = request.build_absolute_uri(
                    produto.imagem.url
                )
            else:
                item.imagem_url = None

            item.save(
                update_fields=[
                    'preco',
                    'nome',
                    'quantidade',
                    'imagem_url'
                ]
            )

            # A peça foi vendida
            produto.disponivel = False
            produto.save(
                update_fields=['disponivel']
            )

        pedido.status = 'PAGO'
        pedido.save(
            update_fields=['status']
        )

        Venda.objects.get_or_create(
            pedido=pedido,
            defaults={
                'vendedor': vendedor
            }
        )

        return Response(
            {
                'detail': (
                    'Compra realizada com sucesso.'
                ),
                'pedido_id': pedido.id,
                'status': pedido.status,
            },
            status=status.HTTP_200_OK
        )
