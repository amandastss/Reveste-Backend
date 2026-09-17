from rest_framework import serializers

from core.models import Review, ReviewImage


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['image']


class ReviewSerializer(serializers.ModelSerializer):
    userName = serializers.CharField(source='user.username', read_only=True)
    userAvatar = serializers.ImageField(source='user.profile_image', read_only=True)
    produto = serializers.PrimaryKeyRelatedField(read_only=True)
    produto_id = serializers.IntegerField(write_only=True, required=False)
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'produto',
            'produto_id',
            'userName',
            'userAvatar',
            'stars',
            'text',
            'created_at',
            'images',
        ]
        read_only_fields = ['id', 'produto', 'userName', 'userAvatar', 'created_at', 'images']

    def create(self, validated_data):
        produto_id = validated_data.pop('produto_id', None)
        review = Review.objects.create(
            **validated_data,
            produto_id=produto_id,
        )
        return review
