import hashlib
import hmac
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Pedido, Produto, Venda

logger = logging.getLogger(__name__)
MP_API = 'https://api.mercadopago.com'


def _mp_headers(idempotency_key=None):
    token = getattr(settings, 'MERCADO_PAGO_ACCESS_TOKEN', '')
    if not token:
        raise RuntimeError('O servidor não está configurado para pagamentos Mercado Pago.')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    if idempotency_key:
        headers['X-Idempotency-Key'] = idempotency_key
    return headers


def _mp_call(method, path, payload=None, idempotency_key=None):
    response = requests.request(method, f'{MP_API}{path}', headers=_mp_headers(idempotency_key), json=payload, timeout=20)
    try:
        data = response.json()
    except ValueError:
        data = {}
    if not response.ok:
        logger.warning('Mercado Pago HTTP %s: %s', response.status_code, data.get('message', 'erro'))
        raise ValueError('O Mercado Pago não conseguiu processar a solicitação. Confira os dados e tente novamente.')
    return data


def _total(pedido):
    from decimal import Decimal
    return sum((Decimal(str(i.preco if i.preco is not None else i.produto.preco))*i.quantidade for i in pedido.itens.select_related('produto').all()), Decimal('0.00')).quantize(Decimal('0.01'))


def _instructions(data):
    interaction = (data.get('point_of_interaction') or {}).get('transaction_data') or {}
    details = data.get('transaction_details') or {}
    return {'payment_method_id':data.get('payment_method_id'),'qr_code':interaction.get('qr_code'),'qr_code_base64':interaction.get('qr_code_base64'),'ticket_url':details.get('external_resource_url')}


def _confirm(pedido, data):
    if str(data.get('external_reference') or '') != str(pedido.id):
        raise ValueError('A referência do pagamento não corresponde ao pedido.')
    if data.get('status') != 'approved':
        return pedido
    if data.get('currency_id') != 'BRL':
        raise ValueError('A moeda do pagamento não corresponde ao real brasileiro.')
    try:
        amount = Decimal(str(data.get('transaction_amount'))).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('O Mercado Pago não retornou um valor válido.')
    if amount != _total(pedido):
        raise ValueError('O valor pago não corresponde ao total do pedido.')
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if pedido.status == 'PAGO':
        return pedido
    if pedido.status != 'AGUARDANDO_PAGAMENTO':
        raise ValueError('O pedido não está aguardando pagamento.')
    items = list(pedido.itens.select_related('produto').all())
    if not items:
        raise ValueError('O pedido não possui itens.')
    sellers = set()
    for item in items:
        product = Produto.objects.select_for_update().filter(pk=item.produto_id).first()
        if not product or product.reserva_pedido_id != pedido.id:
            raise ValueError('A reserva de uma das peças não corresponde a este pedido.')
        if product.vendedor_id == pedido.usuario_id or item.quantidade != 1:
            raise ValueError('O pedido contém uma peça inválida.')
        sellers.add(product.vendedor_id)
        product.disponivel = False
        product.reserva_pedido = None
        product.reservado_ate = None
        product.save(update_fields=['disponivel','reserva_pedido','reservado_ate'])
    if len(sellers) != 1:
        raise ValueError('O pedido deve conter peças de um único vendedor.')
    pedido.status = 'PAGO'
    pedido.mercado_pago_payment_id = str(data.get('id'))
    pedido.mercado_pago_status = data.get('status')
    pedido.mercado_pago_status_detail = data.get('status_detail')
    pedido.pago_em = timezone.now()
    pedido.save(update_fields=['status','mercado_pago_payment_id','mercado_pago_status','mercado_pago_status_detail','pago_em'])
    vendedor_id = next(iter(sellers))
    venda = Venda.objects.filter(pedido=pedido).order_by('id').first()
    if venda is None:
        Venda.objects.create(pedido=pedido, vendedor_id=vendedor_id)
    elif venda.vendedor_id is None:
        venda.vendedor_id = vendedor_id
        venda.save(update_fields=['vendedor'])
    return pedido


class CriarCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        order = Pedido.objects.select_for_update().filter(usuario=request.user,status='AGUARDANDO_PAGAMENTO').order_by('-id').first()
        if order and order.mercado_pago_payment_id:
            try:
                payment = _mp_call('GET', f'/v1/payments/{order.mercado_pago_payment_id}')
                if str(payment.get('external_reference')) != str(order.id):
                    return Response({'detail':'A cobrança existente não corresponde ao pedido.'},status=status.HTTP_409_CONFLICT)
                if payment.get('status') == 'approved':
                    _confirm(order,payment)
                return Response({'pedido_id':order.id,'status':order.status,'amount':float(_total(order)),'payer_email':request.user.email,'payment_in_progress':True,'payment_status':payment.get('status'),**_instructions(payment)})
            except (RuntimeError, ValueError, requests.RequestException):
                return Response({'detail':'Não foi possível consultar a cobrança existente. Não tente pagar novamente até consultar o pedido.'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if order is None:
            order=Pedido.objects.select_for_update().filter(usuario=request.user,status='PENDENTE').order_by('id').first()
        if order is None:
            return Response({'detail':'Nenhum pedido disponível para pagamento foi encontrado.'},status=status.HTTP_404_NOT_FOUND)
        items=list(order.itens.select_related('produto').all())
        if not items:
            return Response({'detail':'O pedido não possui itens.'},status=status.HTTP_400_BAD_REQUEST)
        sellers=set()
        now=timezone.now()
        for item in items:
            product=Produto.objects.select_for_update().filter(pk=item.produto_id).first()
            if not product or not product.disponivel:
                return Response({'detail':'Uma das peças não está mais disponível.'},status=status.HTTP_409_CONFLICT)
            if product.vendedor_id==request.user.id:
                return Response({'detail':'Você não pode comprar sua própria peça.'},status=status.HTTP_400_BAD_REQUEST)
            if product.reserva_pedido_id and product.reserva_pedido_id!=order.id:
                previous=Pedido.objects.filter(pk=product.reserva_pedido_id).first()
                active=bool(product.reservado_ate and product.reservado_ate>now)
                in_payment=bool(previous and previous.status=='AGUARDANDO_PAGAMENTO' and previous.mercado_pago_payment_id)
                if active or in_payment:
                    return Response({'detail':f'A peça "{product.nome}" está reservada por outra compra.'},status=status.HTTP_409_CONFLICT)
            sellers.add(product.vendedor_id)
            item.preco=product.preco
            item.nome=product.nome
            item.save(update_fields=['preco','nome'])
            product.reserva_pedido=order
            product.reservado_ate=now+timedelta(minutes=30)
            product.save(update_fields=['reserva_pedido','reservado_ate'])
        if len(sellers)!=1:
            return Response({'detail':'O pedido deve conter peças de um único vendedor.'},status=status.HTTP_400_BAD_REQUEST)
        order.status='AGUARDANDO_PAGAMENTO'
        order.mercado_pago_idempotency_key=str(uuid4())
        order.save(update_fields=['status','mercado_pago_idempotency_key'])
        return Response({'pedido_id':order.id,'status':order.status,'amount':float(_total(order)),'payer_email':request.user.email,'payment_in_progress':False})


class ProcessarPagamentoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id=request.data.get('pedido_id')
        order=Pedido.objects.filter(pk=order_id,usuario=request.user).first()
        if not order:
            return Response({'detail':'Pedido não encontrado.'},status=status.HTTP_404_NOT_FOUND)
        if order.status=='PAGO':
            return Response({'pedido_id':order.id,'id':order.mercado_pago_payment_id,'status':'approved'})
        if order.status!='AGUARDANDO_PAGAMENTO':
            return Response({'detail':'O pedido não está aguardando pagamento.'},status=status.HTTP_409_CONFLICT)
        if order.mercado_pago_payment_id:
            return Response({'detail':'Este pedido já possui uma cobrança. Consulte o pedido antes de tentar novamente.'},status=status.HTTP_409_CONFLICT)
        method=str(request.data.get('payment_method_id') or '').strip()
        if not method:
            return Response({'detail':'Escolha uma forma de pagamento.'},status=status.HTTP_400_BAD_REQUEST)
        payer_data=request.data.get('payer') or {}
        if not isinstance(payer_data,dict):
            payer_data={}
        payer={'email':request.user.email}
        ident=payer_data.get('identification') or {}
        if isinstance(ident,dict) and ident.get('type') and ident.get('number'):
            digits=''.join(c for c in str(ident['number']) if c.isdigit())
            payer['identification']={'type':str(ident['type']).upper(),'number':digits}
        payload={'transaction_amount':float(_total(order)),'description':f'Reveste - Pedido #{order.id}','payment_method_id':method,'external_reference':str(order.id),'payer':payer}
        notification_url=getattr(settings,'MERCADO_PAGO_WEBHOOK_URL','')
        if notification_url:
            payload['notification_url']=notification_url
        if method=='pix':
            pass
        elif method in {'bolbradesco','ticket'}:
            address=payer_data.get('address') or {}
            fields=('street_name','street_number','neighborhood','city','federal_unit','zip_code')
            if not isinstance(address,dict) or any(not str(address.get(f,'')).strip() for f in fields):
                return Response({'detail':'Para gerar o boleto, preencha o endereço completo no formulário.'},status=status.HTTP_400_BAD_REQUEST)
            if not payer.get('identification') or len(payer['identification']['number'])!=11:
                return Response({'detail':'Informe um CPF válido para gerar o boleto.'},status=status.HTTP_400_BAD_REQUEST)
            payer['address']={f:str(address[f]).strip() for f in fields}
            payer['address']['zip_code']=''.join(c for c in payer['address']['zip_code'] if c.isdigit())
            if len(payer['address']['zip_code'])!=8:
                return Response({'detail':'O CEP deve conter oito dígitos.'},status=status.HTTP_400_BAD_REQUEST)
            for f in ('first_name','last_name'):
                if payer_data.get(f): payer[f]=str(payer_data[f]).strip()
        else:
            token=request.data.get('token')
            if not isinstance(token,str) or not token.strip():
                return Response({'detail':'O formulário não gerou um token de cartão válido.'},status=status.HTTP_400_BAD_REQUEST)
            try: installments=int(request.data.get('installments',1))
            except (TypeError,ValueError): installments=0
            if installments<1:
                return Response({'detail':'Número de parcelas inválido.'},status=status.HTTP_400_BAD_REQUEST)
            payload.update({'token':token,'installments':installments})
            if request.data.get('issuer_id'): payload['issuer_id']=request.data['issuer_id']
        key=order.mercado_pago_idempotency_key or str(uuid4())
        try:
            data=_mp_call('POST','/v1/payments',payload,key)
        except RuntimeError as exc:
            return Response({'detail':str(exc)},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (ValueError,requests.RequestException):
            return Response({'detail':'O Mercado Pago não conseguiu processar o pagamento. Confira os dados antes de tentar novamente.'},status=status.HTTP_502_BAD_GATEWAY)
        with transaction.atomic():
            order=Pedido.objects.select_for_update().get(pk=order.pk,usuario=request.user)
            if order.mercado_pago_payment_id and str(order.mercado_pago_payment_id)!=str(data.get('id')):
                return Response({'detail':'O pedido já possui outra cobrança registrada.'},status=status.HTTP_409_CONFLICT)
            order.mercado_pago_payment_id=str(data.get('id')) if data.get('id') else None
            order.mercado_pago_status=data.get('status')
            order.mercado_pago_status_detail=data.get('status_detail')
            order.mercado_pago_idempotency_key=key
            order.save(update_fields=['mercado_pago_payment_id','mercado_pago_status','mercado_pago_status_detail','mercado_pago_idempotency_key'])
            if data.get('status')=='approved':
                try: _confirm(order,data)
                except ValueError:
                    logger.exception('Pagamento aprovado não pôde confirmar pedido %s',order.id)
                    return Response({'detail':'O pagamento foi recebido, mas a confirmação automática falhou. Entre em contato com o suporte.','pedido_id':order.id,'status':'in_process'},status=status.HTTP_409_CONFLICT)
            elif data.get('status') in {'rejected','cancelled'}:
                order.status='CANCELADO'
                order.save(update_fields=['status'])
                Produto.objects.filter(reserva_pedido=order).update(reserva_pedido=None,reservado_ate=None)
        return Response({'pedido_id':order.id,'id':data.get('id'),'status':data.get('status'),'status_detail':data.get('status_detail'),**_instructions(data)})


class MercadoPagoWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        secret=getattr(settings,'MERCADO_PAGO_WEBHOOK_SECRET','')
        signature=request.headers.get('x-signature','')
        request_id=request.headers.get('x-request-id','')
        body_data=request.data.get('data') if isinstance(request.data,dict) else {}
        payment_id=str(request.query_params.get('data.id') or (body_data or {}).get('id') or '')
        if not secret or not signature or not request_id or not payment_id:
            return Response({'detail':'Webhook não autenticado.'},status=status.HTTP_401_UNAUTHORIZED)
        parts=dict(part.strip().split('=',1) for part in signature.split(',') if '=' in part)
        timestamp,received=parts.get('ts'),parts.get('v1')
        if not timestamp or not received:
            return Response({'detail':'Assinatura inválida.'},status=status.HTTP_401_UNAUTHORIZED)
        manifest=f'id:{payment_id};request-id:{request_id};ts:{timestamp};'
        expected=hmac.new(secret.encode(),manifest.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,received):
            return Response({'detail':'Assinatura inválida.'},status=status.HTTP_401_UNAUTHORIZED)
        try: data=_mp_call('GET',f'/v1/payments/{payment_id}')
        except (RuntimeError,ValueError,requests.RequestException):
            return Response({'detail':'Não foi possível consultar o pagamento.'},status=status.HTTP_503_SERVICE_UNAVAILABLE)
        order_id=data.get('external_reference')
        if not order_id: return Response({'received':True})
        with transaction.atomic():
            order=Pedido.objects.select_for_update().filter(pk=order_id).first()
            if not order or str(order.mercado_pago_payment_id or '')!=str(data.get('id')):
                return Response({'received':True})
            if data.get('status')=='approved':
                try: _confirm(order,data)
                except ValueError:
                    logger.exception('Webhook inválido para pedido %s',order.id)
                    return Response({'detail':'Pagamento não corresponde ao pedido.'},status=status.HTTP_409_CONFLICT)
            elif data.get('status') in {'rejected','cancelled'} and order.status!='PAGO':
                order.status='CANCELADO'
                order.mercado_pago_status=data.get('status')
                order.mercado_pago_status_detail=data.get('status_detail')
                order.save(update_fields=['status','mercado_pago_status','mercado_pago_status_detail'])
                Produto.objects.filter(reserva_pedido=order).update(reserva_pedido=None,reservado_ate=None)
        return Response({'received':True})
