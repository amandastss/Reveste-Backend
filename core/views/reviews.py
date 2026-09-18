from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from core.models import Review, ReviewImage
from core.serializers import ReviewSerializer


class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Review.objects.all().order_by('-created_at')
        produto_id = self.request.query_params.get('produto_id')

        if produto_id is not None:
            queryset = queryset.filter(produto_id=produto_id)

        return queryset

    def perform_create(self, serializer):
        produto_id = self.request.data.get('produto_id')

        if not produto_id:
            raise ValueError('produto_id é obrigatório para criar uma review.')

        review = serializer.save(
            user=self.request.user,
            produto_id=produto_id
        )

        images = self.request.FILES.getlist('images')

        for img in images:
            ReviewImage.objects.create(review=review, image=img)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)


class ReviewListCreateView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, produto_id):
        reviews = Review.objects.filter(
            produto_id=produto_id
        ).order_by('-created_at')

        serializer = ReviewSerializer(reviews, many=True)

        return Response(serializer.data)

    def post(self, request, produto_id):
        review = Review.objects.create(
            user=request.user,
            produto_id=produto_id,
            stars=request.data.get('stars'),
            text=request.data.get('text')
        )

        images = request.FILES.getlist('images')

        for img in images:
            ReviewImage.objects.create(
                review=review,
                image=img
            )

        serializer = ReviewSerializer(review)

        return Response(serializer.data)

    def delete(self, request, produto_id):
        review_id = request.data.get('review_id')

        if not review_id:
            return Response(
                {'detail': 'review_id é obrigatório.'},
                status=400
            )

        try:
            review = Review.objects.get(
                id=review_id,
                produto_id=produto_id,
                user=request.user
            )
        except Review.DoesNotExist:
            return Response(
                {
                    'detail': (
                        'Avaliação não encontrada '
                        'ou não pertence ao usuário.'
                    )
                },
                status=404
            )

        review.delete()

        return Response(status=204)
