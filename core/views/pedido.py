from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from ..models import Pedido
from ..serializers.pedido import PedidoSerializer


class PedidoViewSet(ReadOnlyModelViewSet):
    """Lista e consulta exclusivamente os pedidos do usuário autenticado."""
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Pedido.objects
            .filter(usuario=self.request.user)
            .prefetch_related('itens__produto')
            .order_by('-criado_em')
        )


class AtualizarEntregaPedidoView(APIView):
    """Permite ao vendedor da peça avançar o status logístico de um pedido pago."""
    permission_classes = [IsAuthenticated]

    TRANSICOES = {
        'AGUARDANDO_PREPARACAO': {'ENVIADO'},
        'ENVIADO': {'EM_TRANSITO'},
        'EM_TRANSITO': {'SAIU_PARA_ENTREGA'},
        'SAIU_PARA_ENTREGA': {'ENTREGUE'},
    }

    def patch(self, request, pedido_id):
        pedido = (
            Pedido.objects.select_related('venda')
            .filter(pk=pedido_id, venda__vendedor=request.user)
            .first()
        )
        if pedido is None and not request.user.is_staff:
            return Response(
                {'detail': 'Somente o vendedor responsável pode atualizar esta entrega.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if pedido is None:
            pedido = Pedido.objects.filter(pk=pedido_id).first()
        if pedido is None:
            return Response({'detail': 'Pedido não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if pedido.status != 'PAGO':
            return Response(
                {'detail': 'A entrega só pode ser atualizada depois da confirmação do pagamento.'},
                status=status.HTTP_409_CONFLICT,
            )

        novo_status = str(request.data.get('status_entrega', '')).upper()
        permitidos = self.TRANSICOES.get(pedido.status_entrega, set())
        if novo_status not in permitidos:
            return Response(
                {'detail': 'Transição de entrega inválida ou fora de ordem.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pedido.status_entrega = novo_status
        pedido.save(update_fields=['status_entrega', 'atualizado_em'])
        return Response(PedidoSerializer(pedido).data, status=status.HTTP_200_OK)
