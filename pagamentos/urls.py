from django.urls import path

from .views import (
    CriarCheckoutView,
    ProcessarPagamentoView,
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
]