from rest_framework import serializers

from core.models import User


class UserSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(read_only=True)
    endereco_entrega = serializers.JSONField(required=False)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'role', 'birth_date', 'phone', 'bio',
            'profile_image', 'created_at', 'endereco_entrega',
        ]
        read_only_fields = ['id', 'role', 'created_at', 'profile_image']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'password', 'role', 'birth_date',
            'phone', 'bio', 'profile_image', 'endereco_entrega',
        ]

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'buyer'),
            name=validated_data.get('name', ''),
            birth_date=validated_data.get('birth_date'),
            phone=validated_data.get('phone', ''),
            bio=validated_data.get('bio', ''),
            profile_image=validated_data.get('profile_image'),
            endereco_entrega=validated_data.get('endereco_entrega', {}),
        )
