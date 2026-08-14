from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Review, ReviewImage
from ..serializers import ReviewSerializer


class ReviewListCreateView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, produto_id):
        reviews = Review.objects.filter(produto_id=produto_id).order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    def post(self, request, produto_id):
        review = Review.objects.create(
            user=request.user, produto_id=produto_id, stars=request.data.get('stars'), text=request.data.get('text')
        )

        images = request.FILES.getlist('images')

        for img in images:
            ReviewImage.objects.create(review=review, image=img)

        serializer = ReviewSerializer(review)
        return Response(serializer.data)
