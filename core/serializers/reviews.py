from rest_framework import serializers

from core.models import Review, ReviewImage


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['image']


class ReviewSerializer(serializers.ModelSerializer):
    userName = serializers.CharField(source='user.username', read_only=True)
    userAvatar = serializers.ImageField(source='user.profile_image', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'userName', 'userAvatar', 'stars', 'text', 'created_at', 'images']
