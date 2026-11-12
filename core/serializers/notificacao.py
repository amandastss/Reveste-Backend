from rest_framework import serializers

from core.models import Notificacao


class NotificacaoSerializer(serializers.ModelSerializer):
    produto_id = serializers.IntegerField(read_only=True)
    pergunta_id = serializers.IntegerField(read_only=True)
    link = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Notificacao
        fields = [
            'id',
            'usuario',
            'mensagem',
            'lida',
            'data_envio',
            'produto_id',
            'pergunta_id',
            'link',
        ]
        read_only_fields = [
            'id',
            'usuario',
            'mensagem',
            'data_envio',
            'produto_id',
            'pergunta_id',
            'link',
        ]

    def get_link(self, obj):
        if not obj.produto_id or not obj.pergunta_id:
            return None
        return f'/produto/{obj.produto_id}/perguntas?pergunta_id={obj.pergunta_id}'
