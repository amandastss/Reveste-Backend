from drf_spectacular.utils import extend_schema
from rest_framework import mixins, parsers, viewsets

from uploader.models import Document, Image
from uploader.serializers import DocumentUploadSerializer, ImageUploadSerializer


class CreateViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    pass


class DocumentUploadViewSet(CreateViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentUploadSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "format": "binary"
                    }
                },
                "required": ["file"]
            }
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class ImageUploadViewSet(CreateViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageUploadSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "format": "binary"
                    },
                    "description": {
                        "type": "string"
                    }
                },
                "required": ["file"]
            }
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
