from django.urls import path

from .views import CriarCheckoutView


urlpatterns = [
    path(
        'criar-checkout/',
        CriarCheckoutView.as_view(),
        name='criar-checkout'
    ),
]