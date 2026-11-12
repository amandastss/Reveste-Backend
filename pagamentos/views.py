from datetime import timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import mercadopago
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Pedido, Produto

from .services import confirmar_pagamento


class CriarCheckoutView(APIView):
    """Prepara um pedido para o Payment Brick sem criar preferência Checkout Pro."""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _instrucoes_pagamento(pedido):
        """Recupera instruções existentes para retomar um Pix/boleto sem criar cobrança nova."""
        if not pedido.mercado_pago_payment_id:
            return {}
        token = getattr(settings, 'MERCADO_PAGO_ACCESS_TOKEN', None)
        if not token:
            return {}
        try:
            resposta = mercadopago.SDK(token).payment().get(pedido.mercado_pago_payment_id)
            dados = resposta.get('response') if isinstance(resposta, dict) else None
            if not isinstance(dados, dict):
                return {}
            if str(dados.get('external_reference')) != str(pedido.id):
                return {}
            interaction = (dados.get('point_of_interaction') or {}).get('transaction_data') or {}
            details = dados.get('transaction_details') or {}
            return {
                'payment_status': dados.get('status') or pedido.mercado_pago_status,
                'payment_method_id': dados.get('payment_method_id'),
                'qr_code': interaction.get('qr_code'),
                'qr_code_base64': interaction.get('qr_code_base64'),
                'ticket_url': details.get('external_resource_url'),
            }
        except Exception:
            # Não cria outra cobrança se a consulta do gateway falhar.
            return {'payment_status': pedido.mercado_pago_status}

    @transaction.atomic
    def post(self, request):
        pedido_com_pagamento = (
            Pedido.objects.select_for_update()
            .filter(usuario=request.user, status='AGUARDANDO_PAGAMENTO')
            .exclude(mercado_pago_payment_id__isnull=True)
            .order_by('-atualizado_em')
            .first()
        )
        if pedido_com_pagamento is not None:
            total_existente = sum(
                (Decimal(str(item.preco)) * item.quantidade for item in pedido_com_pagamento.itens.all()),
                Decimal('0.00'),
            )
            return Response({
                'pedido_id': pedido_com_pagamento.id,
                'status': pedido_com_pagamento.status,
                'amount': float(total_existente),
                'payer_email': request.user.email,
                'payment_in_progress': True,
                **self._instrucoes_pagamento(pedido_com_pagamento),
            }, status=status.HTTP_200_OK)

        # Retome primeiro o pedido que já reservou a peça. Criar outro pedido
        # PENDENTE antes dele fazia o checkout disputar a própria reserva e
        # retornava 409 mesmo quando a compradora era a mesma.
        pedido = (
            Pedido.objects.select_for_update()
            .filter(
                usuario=request.user,
                status='AGUARDANDO_PAGAMENTO',
                mercado_pago_payment_id__isnull=True,
            )
            .order_by('-atualizado_em', '-id')
            .first()
        )
        if pedido is None:
            pedido = (
                Pedido.objects.select_for_update()
                .filter(usuario=request.user, status='PENDENTE')
                .order_by('id')
                .first()
            )
        if pedido is None:
            return Response(
                {'detail': 'Nenhum pedido disponível para pagamento foi encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        itens = list(pedido.itens.select_related('produto__user').all())
        if not itens:
            return Response({'detail': 'O pedido não possui itens.'}, status=status.HTTP_400_BAD_REQUEST)

        # Se já existe uma tentativa no gateway, não criamos outra cobrança.
        if pedido.mercado_pago_payment_id:
            total_existente = sum(
                (Decimal(str(item.preco)) * item.quantidade for item in itens),
                Decimal('0.00'),
            )
            return Response({
                'pedido_id': pedido.id,
                'status': pedido.status,
                'amount': float(total_existente),
                'payer_email': request.user.email,
                'payment_in_progress': True,
                'payment_status': pedido.mercado_pago_status,
            }, status=status.HTTP_200_OK)

        agora = timezone.now()
        vendedores = set()
        total = Decimal('0.00')
        produtos_vistos = set()
        produtos = []

        for item in itens:
            produto = Produto.objects.select_for_update().filter(pk=item.produto_id).first()
            if produto is None:
                return Response(
                    {'detail': f'A peça "{item.nome or "Peça"}" não foi encontrada.'},
                    status=status.HTTP_409_CONFLICT,
                )
            # Uma reserva pode deixar o produto indisponível no catálogo.
            # Permita chegar à validação da reserva se ela pertence ao pedido
            # atual ou a um checkout anterior da mesma compradora; reservas de
            # terceiros continuam bloqueadas abaixo.
            if not produto.disponivel:
                reserva_atual = (
                    Pedido.objects.filter(pk=produto.reserva_pedido_id).only('usuario_id').first()
                    if produto.reserva_pedido_id else None
                )
                reserva_da_compradora = (
                    produto.reserva_pedido_id == pedido.id
                    or (
                        reserva_atual is not None
                        and reserva_atual.usuario_id == request.user.id
                    )
                )
                if not reserva_da_compradora:
                    return Response(
                        {'detail': f'A peça "{produto.nome or item.nome or "Peça"}" não está mais disponível.'},
                        status=status.HTTP_409_CONFLICT,
                    )
            if produto.user_id == request.user.id:
                return Response(
                    {'detail': 'Você não pode comprar sua própria peça.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if item.quantidade != 1:
                return Response(
                    {'detail': 'Cada peça do brechó possui apenas uma unidade disponível.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if produto.id in produtos_vistos:
                return Response(
                    {'detail': 'O pedido contém uma peça duplicada.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if produto.reserva_pedido_id and produto.reserva_pedido_id != pedido.id:
                reserva_anterior = (
                    Pedido.objects.select_for_update()
                    .filter(pk=produto.reserva_pedido_id)
                    .first()
                )
                reserva_expirada = (
                    produto.reservado_ate is None
                    or produto.reservado_ate <= agora
                )
                # Só podemos tomar a reserva de um checkout abandonado se o
                # gateway ainda não tiver sido chamado. Uma chave de idempotência
                # sem ID de pagamento é ambígua e exige reconciliação, não liberação.
                reserva_sem_cobranca = (
                    reserva_anterior is None
                    or (
                        not reserva_anterior.mercado_pago_payment_id
                        and not reserva_anterior.mercado_pago_idempotency_key
                    )
                )
                mesma_compradora = (
                    reserva_anterior is not None
                    and reserva_anterior.usuario_id == request.user.id
                )
                pode_liberar = reserva_sem_cobranca and (
                    reserva_expirada or mesma_compradora
                )
                if not pode_liberar:
                    return Response(
                        {'detail': f'A peça "{produto.nome}" está reservada em outro checkout. Se for uma tentativa anterior sua, consulte Meus pedidos ou aguarde a expiração da reserva.'},
                        status=status.HTTP_409_CONFLICT,
                    )
                if reserva_anterior is not None and mesma_compradora:
                    # A compradora iniciou outro checkout sem ter enviado uma
                    # cobrança ao gateway. Cancela o checkout antigo e libera
                    # suas reservas para o pedido atual, sem marcar peças vendidas.
                    if reserva_anterior.status == 'AGUARDANDO_PAGAMENTO':
                        reserva_anterior.status = 'CANCELADO'
                        reserva_anterior.save(update_fields=['status', 'atualizado_em'])
                    Produto.objects.filter(reserva_pedido=reserva_anterior).update(
                        reserva_pedido=None,
                        reservado_ate=None,
                    )

            produtos_vistos.add(produto.id)
            vendedores.add(produto.user_id)
            produtos.append((item, produto))
            total += Decimal(str(produto.preco))

        if len(vendedores) != 1:
            return Response(
                {'detail': 'Todos os itens do pedido devem pertencer ao mesmo vendedor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if total <= Decimal('0.00'):
            return Response(
                {'detail': 'O total do pedido precisa ser maior que zero.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Só grava alterações depois que todos os itens passaram pela validação.
        expiracao = agora + timedelta(minutes=15)
        for item, produto in produtos:
            item.preco = produto.preco
            item.nome = produto.nome
            item.save(update_fields=['preco', 'nome'])
            produto.reserva_pedido = pedido
            produto.reservado_ate = expiracao
            produto.save(update_fields=['reserva_pedido', 'reservado_ate'])

        pedido.status = 'AGUARDANDO_PAGAMENTO'
        pedido.save(update_fields=['status', 'atualizado_em'])

        return Response({
            'pedido_id': pedido.id,
            'status': pedido.status,
            'amount': float(total),
            'payer_email': request.user.email,
        }, status=status.HTTP_200_OK)



class ProcessarPagamentoView(APIView):
    """Recebe o token do Payment Brick e cria o pagamento usando o token privado."""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _criar_pagamento_mp(payload, idempotency_key):
        token = getattr(settings, 'MERCADO_PAGO_ACCESS_TOKEN', None)
        if not token:
            return None, {'detail': 'Token privado do Mercado Pago não configurado.'}, status.HTTP_502_BAD_GATEWAY

        request_options = mercadopago.config.RequestOptions()
        request_options.custom_headers = {'x-idempotency-key': idempotency_key}
        try:
            resposta = mercadopago.SDK(token).payment().create(payload, request_options)
        except Exception:
            return (
                None,
                {'detail': 'Não foi possível comunicar com o Mercado Pago. Consulte o pedido antes de tentar novamente.'},
                status.HTTP_502_BAD_GATEWAY,
            )

        dados = resposta.get('response') if isinstance(resposta, dict) else None
        if not isinstance(dados, dict) or not dados.get('id') or not dados.get('status'):
            # Retorna uma mensagem acionável sem expor tokens ou dados sensíveis.
            mensagem = 'O Mercado Pago não aceitou os dados do pagamento.'
            causas = dados.get('cause', []) if isinstance(dados, dict) else []
            descricao = dados.get('message') if isinstance(dados, dict) else None
            if causas and isinstance(causas, list):
                descricoes = [
                    str(causa.get('description') or causa.get('code'))
                    for causa in causas[:3] if isinstance(causa, dict)
                ]
                if descricoes:
                    mensagem += ' ' + ' '.join(descricoes)
            elif descricao:
                mensagem += ' ' + str(descricao)
            return (
                None,
                {'detail': mensagem, 'gateway_status': resposta.get('status') if isinstance(resposta, dict) else None},
                status.HTTP_400_BAD_REQUEST,
            )
        return dados, None, None

    @staticmethod
    def _payload_pagamento(request, pedido, total):
        token = request.data.get('token')
        payment_method_id = request.data.get('payment_method_id')
        try:
            installments = int(request.data.get('installments', 1))
        except (TypeError, ValueError):
            installments = 0

        if not isinstance(token, str) or not token.strip():
            return None, 'Token de pagamento obrigatório.'
        if not isinstance(payment_method_id, str) or not payment_method_id.strip():
            return None, 'Método de pagamento obrigatório.'
        if installments < 1:
            return None, 'Quantidade de parcelas inválida.'

        payer = {'email': request.user.email}
        payer_data = request.data.get('payer') or {}
        identification = payer_data.get('identification') or {}
        if identification.get('type') and identification.get('number'):
            payer['identification'] = {
                'type': identification['type'],
                'number': identification['number'],
            }

        payload = {
            'transaction_amount': float(total),
            'token': token,
            'description': f'Compra Reveste - Pedido #{pedido.id}',
            'installments': installments,
            'payment_method_id': payment_method_id,
            'external_reference': str(pedido.id),
            'payer': payer,
        }
        notification_url = getattr(settings, 'MERCADO_PAGO_WEBHOOK_URL', None)
        if notification_url:
            payload['notification_url'] = notification_url
        issuer_id = request.data.get('issuer_id')
        if issuer_id:
            payload['issuer_id'] = issuer_id
        return payload, None

    @staticmethod
    def _registrar_pagamento_para_reconciliacao(dados, pedido):
        # Nunca permita uma nova tentativa automática se o gateway reportou
        # aprovação, mas os dados não podem ser conciliados com o pedido.
        pedido.mercado_pago_payment_id = str(dados.get('id'))
        pedido.mercado_pago_status = dados.get('status')
        pedido.mercado_pago_status_detail = dados.get('status_detail')
        pedido.save(update_fields=[
            'mercado_pago_payment_id',
            'mercado_pago_status',
            'mercado_pago_status_detail',
            'atualizado_em',
        ])

    @staticmethod
    def _resposta_pagamento(dados, pedido):
        mp_status = dados.get('status')
        payment_id = dados.get('id')

        # Nenhum estado pode ser associado a um pedido diferente.
        if str(dados.get('external_reference')) != str(pedido.id):
            return Response(
                {'detail': 'O pagamento retornado não corresponde ao pedido.'},
                status=status.HTTP_409_CONFLICT,
            )

        if mp_status == 'approved':
            try:
                valor_gateway = Decimal(str(dados.get('transaction_amount'))).quantize(Decimal('0.01'))
                valor_pedido = sum(
                    (Decimal(str(item.preco)) * item.quantidade for item in pedido.itens.all()),
                    Decimal('0.00'),
                ).quantize(Decimal('0.01'))
            except (InvalidOperation, TypeError, ValueError):
                ProcessarPagamentoView._registrar_pagamento_para_reconciliacao(dados, pedido)
                return Response(
                    {'detail': 'O pagamento foi criado, mas seu valor precisa ser verificado pelo suporte.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if valor_gateway != valor_pedido or dados.get('currency_id') != 'BRL':
                ProcessarPagamentoView._registrar_pagamento_para_reconciliacao(dados, pedido)
                return Response(
                    {'detail': 'O pagamento foi criado, mas o valor ou a moeda precisa ser verificado pelo suporte.'},
                    status=status.HTTP_409_CONFLICT,
                )
            try:
                confirmar_pagamento(
                    pedido_id=pedido.id,
                    payment_id=payment_id,
                    payment_status=mp_status,
                    status_detail=dados.get('status_detail'),
                    transaction_amount=valor_gateway,
                    currency_id=dados.get('currency_id'),
                )
            except ValueError:
                ProcessarPagamentoView._registrar_pagamento_para_reconciliacao(dados, pedido)
                return Response(
                    {'detail': 'O gateway aprovou o pagamento, mas o pedido precisa de conciliação manual.'},
                    status=status.HTTP_409_CONFLICT,
                )
        elif mp_status in {'pending', 'in_process'}:
            pedido.mercado_pago_payment_id = str(payment_id)
            pedido.mercado_pago_status = mp_status
            pedido.mercado_pago_status_detail = dados.get('status_detail')
            pedido.save(update_fields=[
                'mercado_pago_payment_id', 'mercado_pago_status',
                'mercado_pago_status_detail', 'atualizado_em',
            ])
        elif mp_status in {'rejected', 'cancelled'}:
            pedido.mercado_pago_payment_id = str(payment_id)
            pedido.mercado_pago_status = mp_status
            pedido.mercado_pago_status_detail = dados.get('status_detail')
            pedido.status = 'CANCELADO'
            Produto.objects.filter(reserva_pedido=pedido).update(reserva_pedido=None, reservado_ate=None)
            pedido.save(update_fields=[
                'status', 'mercado_pago_payment_id', 'mercado_pago_status',
                'mercado_pago_status_detail', 'atualizado_em',
            ])
        else:
            return Response(
                {'detail': 'O Mercado Pago retornou um estado de pagamento que exige verificação.'},
                status=status.HTTP_409_CONFLICT,
            )

        return Response({
            'id': payment_id,
            'status': mp_status,
            'status_detail': dados.get('status_detail'),
            'pedido_id': pedido.id,
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        pedido_id = request.data.get('pedido_id')
        if not pedido_id:
            return Response({'detail': 'ID do pedido é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pedido_id = int(pedido_id)
        except (TypeError, ValueError):
            return Response({'detail': 'ID do pedido inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        pedido = (
            Pedido.objects.select_for_update()
            .filter(id=pedido_id, usuario=request.user)
            .first()
        )
        if pedido is None:
            return Response({'detail': 'Pedido não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if pedido.status == 'PAGO':
            return Response({'detail': 'Este pedido já foi pago.'}, status=status.HTTP_409_CONFLICT)
        if pedido.status != 'AGUARDANDO_PAGAMENTO':
            return Response(
                {'detail': 'O pedido não está preparado para receber pagamento.'},
                status=status.HTTP_409_CONFLICT,
            )
        if pedido.mercado_pago_payment_id:
            return Response(
                {'detail': 'Este pedido já possui um pagamento iniciado. Consulte o estado do pedido antes de tentar novamente.'},
                status=status.HTTP_409_CONFLICT,
            )

        itens = list(pedido.itens.select_related('produto').all())
        if not itens:
            return Response({'detail': 'O pedido não possui itens.'}, status=status.HTTP_400_BAD_REQUEST)

        total = Decimal('0.00')
        vendedores = set()
        produtos = []
        agora = timezone.now()
        for item in itens:
            produto = Produto.objects.select_for_update().filter(pk=item.produto_id).first()
            if produto is None or not produto.disponivel:
                return Response(
                    {'detail': 'Uma ou mais peças não estão mais disponíveis.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if produto.user_id == request.user.id or item.quantidade != 1:
                return Response(
                    {'detail': 'Os itens do pedido não são válidos para pagamento.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if produto.reserva_pedido_id != pedido.id:
                return Response(
                    {'detail': 'A reserva desta peça expirou ou pertence a outro pedido. Atualize o carrinho.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if produto.reservado_ate is None or produto.reservado_ate <= agora:
                pedido.status = 'CANCELADO'
                pedido.save(update_fields=['status', 'atualizado_em'])
                Produto.objects.filter(reserva_pedido=pedido).update(reserva_pedido=None, reservado_ate=None)
                return Response(
                    {'detail': 'A reserva expirou. Atualize o carrinho para verificar a disponibilidade.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if Decimal(str(item.preco)) != Decimal(str(produto.preco)):
                return Response(
                    {'detail': 'O preço de uma peça mudou. Atualize o carrinho e prepare o pedido novamente.'},
                    status=status.HTTP_409_CONFLICT,
                )
            vendedores.add(produto.user_id)
            produtos.append(produto)
            total += Decimal(str(produto.preco)) * item.quantidade

        # Estende a reserva enquanto a tentativa de pagamento está sendo enviada ao gateway.
        nova_expiracao = timezone.now() + timedelta(minutes=30)
        for produto in produtos:
            produto.reservado_ate = nova_expiracao
            produto.save(update_fields=['reservado_ate'])

        if len(vendedores) != 1 or total <= Decimal('0.00'):
            return Response(
                {'detail': 'O pedido precisa conter itens válidos de um único vendedor.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload, erro = self._payload_pagamento(request, pedido, total)
        if erro:
            return Response({'detail': erro}, status=status.HTTP_400_BAD_REQUEST)

        # A mesma chave é reutilizada se a comunicação falhar após o gateway receber a cobrança.
        if not pedido.mercado_pago_idempotency_key:
            pedido.mercado_pago_idempotency_key = str(uuid4())
            pedido.save(update_fields=['mercado_pago_idempotency_key', 'atualizado_em'])

        dados, erro, erro_status = self._criar_pagamento_mp(
            payload,
            pedido.mercado_pago_idempotency_key,
        )
        if erro:
            return Response(erro, status=erro_status)

        return self._resposta_pagamento(dados, pedido)
