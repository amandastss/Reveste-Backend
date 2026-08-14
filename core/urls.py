from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from rest_framework.routers import DefaultRouter

from core.views.compra import CompraViewSet
from core.views.login import LoginView
from core.views.produto import ProdutoViewSet

from .views import HistoricoPesquisaViewSet

router = DefaultRouter()
router.register(r'produtos', ProdutoViewSet)
router.register(r'compras', CompraViewSet)


urlpatterns = [
    path('login/', LoginView.as_view()),
    path(
        'historico/',
        HistoricoPesquisaViewSet.as_view({
            'get': 'list',
            'post': 'create'
        })
    ),
]

urlpatterns = [
]

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)
