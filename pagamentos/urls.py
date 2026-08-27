from django.urls import path

from .views import (
    CriarCheckoutView,
    ProcessarPagamentoView,
)
from .webhooks import (
    MercadoPagoWebhookView,
)


urlpatterns = [

    path(
        'criar-checkout/',
        CriarCheckoutView.as_view(),
        name='criar-checkout'
    ),

    path(
        'processar/',
        ProcessarPagamentoView.as_view(),
        name='processar-pagamento'
    ),

    path(
        'webhook/',
        MercadoPagoWebhookView.as_view(),
        name='mercado-pago-webhook'
    ),
]