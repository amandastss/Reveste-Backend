from django.urls import path

from .brick import ProcessarPagamentoBrickView
from .views import CriarCheckoutView
from .webhooks import MercadoPagoWebhookView

urlpatterns = [
    path(
        'criar-checkout/',
        CriarCheckoutView.as_view(),
        name='criar-checkout',
    ),
    path(
        'processar/',
        ProcessarPagamentoBrickView.as_view(),
        name='processar-pagamento',
    ),
    path(
        'webhook/',
        MercadoPagoWebhookView.as_view(),
        name='mercado-pago-webhook',
    ),
]
