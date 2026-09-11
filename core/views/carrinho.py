from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import ItemPedido, Pedido, Produto
from core.serializers import ItemPedidoSerializer


class CarrinhoView(APIView):
    permission_classes = (IsAuthenticated,)

    # =========================
    # PEGAR O CARRINHO
    # GET /api/carrinho/
    # =========================
    def get(self, request):

        pedido, _ = Pedido.objects.get_or_create(usuario=request.user, status='PENDENTE')

        itens = pedido.itens.select_related('produto').all()

        serializer = ItemPedidoSerializer(itens, many=True, context={'request': request})

        total = sum(item.preco * item.quantidade for item in itens)

        return Response({
            'pedido_id': pedido.id,
            'status': pedido.status,
            'itens': serializer.data,
            'total': total,
        })

    # =========================
    # ADICIONAR AO CARRINHO
    # POST /api/carrinho/
    # =========================
    def post(self, request):

        product_id = request.data.get('productId')

        if not product_id:
            return Response({'detail': 'productId é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            produto = Produto.objects.get(id=product_id, disponivel=True)

        except Produto.DoesNotExist:
            return Response(
                {'detail': ('Produto não encontrado ou não está mais disponível.')}, status=status.HTTP_404_NOT_FOUND
            )

        if produto.user == request.user:
            return Response(
                {'detail': ('Você não pode adicionar seu próprio produto ao carrinho.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pedido, _ = Pedido.objects.get_or_create(usuario=request.user, status='PENDENTE')

        # Não permite adicionar o mesmo produto duas vezes.
        if pedido.itens.filter(produto=produto).exists():
            return Response({'detail': ('Este produto já está no seu carrinho.')}, status=status.HTTP_400_BAD_REQUEST)

        # Mantém a regra de um vendedor por pedido.
        primeiro_item = pedido.itens.select_related('produto__user').first()

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
                    status=status.HTTP_400_BAD_REQUEST,
                )

        item = ItemPedido.objects.create(
            pedido=pedido,
            produto=produto,
            quantidade=1,
            preco=produto.preco,
            nome=produto.nome,
            imagem_url=(request.build_absolute_uri(produto.imagem.url) if produto.imagem else None),
        )

        serializer = ItemPedidoSerializer(item, context={'request': request})

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # =========================
    # REMOVER DO CARRINHO
    # DELETE /api/carrinho/
    # =========================
    def delete(self, request):

        product_id = request.data.get('productId')

        if not product_id:
            return Response({'detail': 'productId é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        pedido = Pedido.objects.filter(usuario=request.user, status='PENDENTE').first()

        if not pedido:
            return Response({'detail': 'Carrinho vazio.'}, status=status.HTTP_404_NOT_FOUND)

        item = pedido.itens.filter(produto_id=product_id).first()

        if not item:
            return Response({'detail': 'Produto não está no carrinho.'}, status=status.HTTP_404_NOT_FOUND)

        item.delete()

        return Response({'detail': 'Produto removido do carrinho.'}, status=status.HTTP_200_OK)


class FinalizarCompraView(APIView):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def _validar_item(item, usuario):

        produto = Produto.objects.filter(id=item.produto_id).first()

        if not produto:
            return f'O produto "{item.nome}" não foi encontrado.'

        if not produto.disponivel:
            return f'O produto "{produto.nome}" não está mais disponível.'

        if produto.user == usuario:
            return 'Você não pode comprar seu próprio produto.'

        if item.quantidade != 1:
            return 'Produtos do brechó possuem apenas uma unidade disponível.'

        return None

    @transaction.atomic
    def post(self, request):

        pedido = Pedido.objects.select_for_update().filter(usuario=request.user, status='PENDENTE').first()

        if not pedido:
            return Response({'detail': ('Nenhum pedido pendente encontrado.')}, status=status.HTTP_404_NOT_FOUND)

        itens = list(pedido.itens.select_related('produto__user').all())

        if not itens:
            return Response({'detail': 'O carrinho está vazio.'}, status=status.HTTP_400_BAD_REQUEST)

        vendedores = set()
        erro_validacao = None

        for item in itens:
            erro_validacao = self._validar_item(item, request.user)

            if erro_validacao:
                break

            vendedores.add(item.produto.user_id)

        if erro_validacao:
            return Response({'detail': erro_validacao}, status=status.HTTP_400_BAD_REQUEST)

        if len(vendedores) != 1:
            return Response(
                {'detail': ('Todos os produtos do carrinho devem pertencer ao mesmo vendedor.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Atualiza os dados do pedido antes do pagamento,
        # mas NÃO marca o pedido como pago.
        for item in itens:
            produto = Produto.objects.get(id=item.produto_id)

            item.preco = produto.preco
            item.nome = produto.nome
            item.quantidade = 1

            if produto.imagem:
                item.imagem_url = request.build_absolute_uri(produto.imagem.url)
            else:
                item.imagem_url = None

            item.save(update_fields=['preco', 'nome', 'quantidade', 'imagem_url'])

        # O pedido continua pendente.
        #
        # A mudança para AGUARDANDO_PAGAMENTO será feita
        # pelo fluxo do Mercado Pago.
        #
        # A mudança para PAGO será feita somente depois
        # da confirmação de pagamento.
        return Response(
            {
                'detail': ('Pedido preparado para pagamento.'),
                'pedido_id': pedido.id,
                'status': pedido.status,
            },
            status=status.HTTP_200_OK,
        )
