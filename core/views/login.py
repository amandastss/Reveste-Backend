import uuid

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.sessaoLogin import SessaoLogin


class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(username=email, password=password)

        if not user:
            return Response(
                {"error": "Credenciais inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # gera token simples (pode melhorar depois)
        token = str(uuid.uuid4())

        SessaoLogin.objects.create(
            usuario=user,
            token=token
        )

        return Response({
            "token": token,
            "user_id": user.id
        })
