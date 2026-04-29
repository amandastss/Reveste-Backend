from rest_framework import serializers

from posts.models import Post
from uploader.models import Image


class PostSerializer(serializers.ModelSerializer):
    image_attachment_key = serializers.UUIDField(write_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["title", "image_attachment_key", "image_url"]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def create(self, validated_data):
        key = validated_data.pop("image_attachment_key", None)

        if key:
            try:
                image = Image.objects.get(attachment_key=key)
                validated_data["image"] = image
            except Image.DoesNotExist:
                pass  # evita quebrar tudo

        return super().create(validated_data)
