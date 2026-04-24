from rest_framework import serializers

from core.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'name',
            'is_active',
            'is_staff',
            'is_superuser',
            'last_login',
            'groups',
            'foto',
            'foto_attachment_key',
        ]
        depth = 1


class UserRegistrationSerializer(serializers.ModelSerializer):  # noqa: F811, F821
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
