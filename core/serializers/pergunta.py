from rest_framework import serializers

from core.models import Pergunta, User


class UserPerguntaSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'profile_image']
        read_only_fields = ['id', 'name', 'email', 'profile_image']

    def get_profile_image(self, obj):
        if not obj or not obj.profile_image:
            return None

        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.profile_image.url)
        return obj.profile_image.url


class PerguntaSerializer(serializers.ModelSerializer):
    user = serializers.IntegerField(source='user_id', read_only=True)
    usuario = UserPerguntaSerializer(source='user', read_only=True)
    user_name = serializers.SerializerMethodField(read_only=True)
    nome = serializers.SerializerMethodField(read_only=True)
    username = serializers.SerializerMethodField(read_only=True)
    foto = serializers.SerializerMethodField(read_only=True)
    photo = serializers.SerializerMethodField(read_only=True)
    profile_image = serializers.SerializerMethodField(read_only=True)
    avatar = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField(read_only=True)
    produto_nome = serializers.SerializerMethodField(read_only=True)
    vendedor_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Pergunta
        fields = [
            'id',
            'produto',
            'produto_nome',
            'user',
            'usuario',
            'user_name',
            'nome',
            'username',
            'foto',
            'photo',
            'profile_image',
            'avatar',
            'image',
            'vendedor_id',
            'texto',
            'resposta',
            'criado_em',
            'respondida_em',
        ]
        read_only_fields = [
            'id',
            'produto_nome',
            'user',
            'usuario',
            'user_name',
            'nome',
            'username',
            'foto',
            'photo',
            'profile_image',
            'avatar',
            'image',
            'vendedor_id',
            'criado_em',
            'respondida_em',
        ]

    def get_user_name(self, obj):
        if obj.user is None:
            return 'Visitante'
        return obj.user.name if hasattr(obj.user, 'name') else obj.user.email

    def get_nome(self, obj):
        return self.get_user_name(obj)

    def get_username(self, obj):
        return self.get_user_name(obj)

    def get_user_profile_image(self, obj):
        if obj.user is None or not obj.user.profile_image:
            return None
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.user.profile_image.url)
        return obj.user.profile_image.url

    def get_foto(self, obj):
        return self.get_user_profile_image(obj)

    def get_photo(self, obj):
        return self.get_user_profile_image(obj)

    def get_profile_image(self, obj):
        return self.get_user_profile_image(obj)

    def get_avatar(self, obj):
        return self.get_user_profile_image(obj)

    def get_image(self, obj):
        return self.get_user_profile_image(obj)

    def get_produto_nome(self, obj):
        return obj.produto.nome

    def get_vendedor_id(self, obj):
        return obj.produto.user_id
