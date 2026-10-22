from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import Notificacao, Pergunta
from core.serializers import PerguntaSerializer


class PerguntaViewSet(ModelViewSet):
    serializer_class = PerguntaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Pergunta.objects.select_related('produto', 'user').order_by('-criado_em')

        produto_id = self.request.query_params.get('produto_id')
        if produto_id is not None:
            queryset = queryset.filter(produto_id=produto_id)

        vendedor = self.request.query_params.get('vendedor')
        if vendedor is not None and vendedor.lower() == 'true':
            queryset = queryset.filter(produto__user=self.request.user)

        return queryset

    def perform_create(self, serializer):
        pergunta = serializer.save(user=self.request.user)

        produto = pergunta.produto
        if produto.user and produto.user != self.request.user:
            Notificacao.objects.create(
                usuario=produto.user,
                mensagem=f"Nova pergunta sobre o produto '{produto.nome}'."
            )

    @action(detail=True, methods=['patch'], url_path='responder')
    def responder(self, request, pk=None):
        pergunta = self.get_object()

        if pergunta.produto.user != request.user:
            return Response(
                {'detail': 'Você só pode responder perguntas dos seus produtos.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        resposta = request.data.get('resposta')
        if not resposta or not str(resposta).strip():
            return Response(
                {'detail': 'A resposta da pergunta é obrigatória.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pergunta.resposta = resposta
        pergunta.respondida_em = timezone.now()
        pergunta.save()

        return Response(PerguntaSerializer(pergunta).data)

    @action(detail=False, methods=['get'], url_path='minhas')
    def minhas(self, request):
        perguntas = Pergunta.objects.filter(produto__user=request.user).order_by('-criado_em')
        serializer = PerguntaSerializer(perguntas, many=True, context={'request': request})
        return Response(serializer.data)
