from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models.itemPedido import ItemPedido
from ..models.pedido import Pedido
from ..models.produto import Produto


def _item_payload(item, request):
    produto = item.produto
    imagem = item.imagem_url or (request.build_absolute_uri(produto.imagem.url) if produto.imagem else None)
    preco = item.preco if item.preco is not None else produto.preco
    return {'id':item.id,'produto':produto.id,'quantidade':item.quantidade,'preco':str(preco),
            'nome':item.nome or produto.nome,'cor':item.cor or '','tamanho':item.tamanho or '',
            'imagem_url':imagem,'total':str(Decimal(str(preco))*item.quantidade)}


class CarrinhoView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        pedido = Pedido.objects.filter(usuario=request.user,status='AGUARDANDO_PAGAMENTO').exclude(mercado_pago_payment_id__isnull=True).order_by('-id').first()
        if pedido is None:
            pedido = Pedido.objects.filter(usuario=request.user,status='PENDENTE').order_by('id').first()
        if pedido is None:
            pedido = Pedido.objects.filter(usuario=request.user,status='AGUARDANDO_PAGAMENTO').order_by('-id').first()
        if not pedido:
            return Response({'pedido_id':None,'status':'VAZIO','itens':[],'total':'0.00'})
        itens = list(pedido.itens.select_related('produto').all())
        total = sum((Decimal(str(i.preco if i.preco is not None else i.produto.preco))*i.quantidade for i in itens),Decimal('0.00'))
        return Response({'pedido_id':pedido.id,'status':pedido.status,'itens':[_item_payload(i,request) for i in itens],'total':str(total)})

    @transaction.atomic
    def post(self, request):
        pagamento_ativo = Pedido.objects.filter(usuario=request.user, status='AGUARDANDO_PAGAMENTO').exclude(mercado_pago_payment_id__isnull=True).exists()
        if pagamento_ativo:
            return Response({'detail':'Você já tem um pagamento em andamento. Consulte o pedido antes de iniciar outra compra.'}, status=status.HTTP_409_CONFLICT)
        product_id=request.data.get('productId')
        if not product_id:
            return Response({'detail':'productId é obrigatório.'},status=status.HTTP_400_BAD_REQUEST)
        produto=Produto.objects.select_for_update().filter(pk=product_id,disponivel=True).first()
        if not produto:
            return Response({'detail':'Produto não encontrado ou indisponível.'},status=status.HTTP_404_NOT_FOUND)
        if produto.vendedor_id==request.user.id:
            return Response({'detail':'Você não pode adicionar seu próprio produto ao carrinho.'},status=status.HTTP_400_BAD_REQUEST)
        if produto.reserva_pedido_id and produto.reservado_ate and produto.reservado_ate>timezone.now():
            reserva=Pedido.objects.filter(pk=produto.reserva_pedido_id).first()
            if reserva and reserva.usuario_id!=request.user.id:
                return Response({'detail':'Esta peça está reservada em outro checkout.'},status=status.HTTP_409_CONFLICT)
        pedido,_=Pedido.objects.get_or_create(usuario=request.user,status='PENDENTE')
        if pedido.itens.filter(produto=produto).exists():
            return Response({'detail':'Este produto já está no carrinho.'},status=status.HTTP_400_BAD_REQUEST)
        primeiro=pedido.itens.select_related('produto').first()
        if primeiro and primeiro.produto.vendedor_id!=produto.vendedor_id:
            return Response({'detail':'O carrinho só pode conter peças de um mesmo vendedor.'},status=status.HTTP_400_BAD_REQUEST)
        imagem=request.build_absolute_uri(produto.imagem.url) if produto.imagem else None
        item=ItemPedido.objects.create(pedido=pedido,produto=produto,quantidade=1,preco=produto.preco,nome=produto.nome,imagem_url=imagem)
        return Response(_item_payload(item,request),status=status.HTTP_201_CREATED)

    @transaction.atomic
    def delete(self, request):
        product_id=request.data.get('productId')
        if not product_id:
            return Response({'detail':'productId é obrigatório.'},status=status.HTTP_400_BAD_REQUEST)
        pedido=Pedido.objects.filter(usuario=request.user,status='PENDENTE').order_by('id').first()
        if not pedido:
            return Response({'detail':'Carrinho vazio.'},status=status.HTTP_404_NOT_FOUND)
        item=pedido.itens.filter(produto_id=product_id).first()
        if not item:
            return Response({'detail':'Produto não está no carrinho.'},status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response({'detail':'Produto removido do carrinho.'})


class FinalizarCompraView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        pedido=Pedido.objects.select_for_update().filter(usuario=request.user,status='AGUARDANDO_PAGAMENTO').order_by('-id').first()
        if pedido:
            return Response({'pedido_id':pedido.id,'status':pedido.status})
        pedido=Pedido.objects.select_for_update().filter(usuario=request.user,status='PENDENTE').order_by('id').first()
        if not pedido:
            return Response({'detail':'Nenhum pedido pendente foi encontrado.'},status=status.HTTP_404_NOT_FOUND)
        itens=list(pedido.itens.select_related('produto').all())
        if not itens:
            return Response({'detail':'O carrinho está vazio.'},status=status.HTTP_400_BAD_REQUEST)
        vendedores=set()
        agora=timezone.now()
        for item in itens:
            produto=Produto.objects.select_for_update().filter(pk=item.produto_id).first()
            if not produto or not produto.disponivel:
                return Response({'detail':'Uma das peças não está mais disponível.'},status=status.HTTP_409_CONFLICT)
            if produto.vendedor_id==request.user.id:
                return Response({'detail':'Você não pode comprar sua própria peça.'},status=status.HTTP_400_BAD_REQUEST)
            if item.quantidade!=1:
                return Response({'detail':'Cada peça do brechó possui apenas uma unidade.'},status=status.HTTP_400_BAD_REQUEST)
            if produto.reserva_pedido_id and produto.reserva_pedido_id!=pedido.id:
                reserva=Pedido.objects.filter(pk=produto.reserva_pedido_id).first()
                ativa=bool(produto.reservado_ate and produto.reservado_ate>agora)
                pagamento_ativo=bool(reserva and reserva.status=='AGUARDANDO_PAGAMENTO' and reserva.mercado_pago_payment_id)
                if ativa or pagamento_ativo:
                    return Response({'detail':f'A peça "{produto.nome}" está reservada por outra compra.'},status=status.HTTP_409_CONFLICT)
            vendedores.add(produto.vendedor_id)
            item.preco=produto.preco
            item.nome=produto.nome
            item.imagem_url=request.build_absolute_uri(produto.imagem.url) if produto.imagem else item.imagem_url
            item.save(update_fields=['preco','nome','imagem_url'])
            produto.reserva_pedido=pedido
            produto.reservado_ate=agora+timedelta(minutes=30)
            produto.save(update_fields=['reserva_pedido','reservado_ate'])
        if len(vendedores)!=1:
            return Response({'detail':'O pedido deve conter peças de um único vendedor.'},status=status.HTTP_400_BAD_REQUEST)
        return Response({'pedido_id':pedido.id,'status':pedido.status})
