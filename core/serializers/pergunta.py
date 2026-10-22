from rest_framework import serializers

from core.models import Pergunta


class PerguntaSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField(read_only=True)
    produto_nome = serializers.SerializerMethodField(read_only=True)
    vendedor_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Pergunta
        fields = [
            'id',
            'produto',
            'produto_nome',
            'user',
            'user_name',
            'vendedor_id',
            'texto',
            'resposta',
            'criado_em',
            'respondida_em',
        ]
        read_only_fields = [
            'id',
            'user',
            'user_name',
            'produto_nome',
            'vendedor_id',
            'criado_em',
            'respondida_em',
        ]

    def get_user_name(self, obj):
        return obj.user.name if hasattr(obj.user, 'name') else obj.user.email

    def get_produto_nome(self, obj):
        return obj.produto.nome

    def get_vendedor_id(self, obj):
        return obj.produto.user_id
