from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from core.views import (
    BuscaImagemViewSet,
    CategoriaViewSet,
    FavoritoViewSet,
    HistoricoPesquisaViewSet,
    ImagemProdutoViewSet,
    ItemPedidoViewSet,
    NotificacaoViewSet,
    PedidoViewSet,
    ProdutoViewSet,
    SeguidorViewSet,
    UserRegistrationView,
    UserViewSet,
    VendaViewSet,
)

# IMPORT CORRETO (só um!)
from core.views.sessaoLogin import LoginView
from uploader.router import router as uploader_router

router = DefaultRouter()

router.register(r'usuarios', UserViewSet, basename='usuarios')
router.register(r'produtos', ProdutoViewSet, basename='produtos')
router.register(r'busca-imagem', BuscaImagemViewSet, basename='busca-imagem')
router.register(r'imagens-produto', ImagemProdutoViewSet, basename='imagens-produto')
router.register(r'categorias', CategoriaViewSet, basename='categorias')
router.register(r'favoritos', FavoritoViewSet, basename='favoritos')
router.register(r'pedidos', PedidoViewSet, basename='pedidos')
router.register(r'itens-pedido', ItemPedidoViewSet, basename='itens-pedido')
router.register(r'vendas', VendaViewSet, basename='vendas')
router.register(r'seguidores', SeguidorViewSet, basename='seguidores')
router.register(r'historico-pesquisa', HistoricoPesquisaViewSet, basename='historico-pesquisa')
router.register(r'notificacoes', NotificacaoViewSet, basename='notificacoes')

urlpatterns = [
    path('admin/', admin.site.urls),

    # DOCS
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/doc/', SpectacularSwaggerView.as_view(url_name='schema')),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema')),

    # AUTH JWT
    path('api/token/', TokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/token/verify/', TokenVerifyView.as_view()),

    # REGISTRO
    path('api/registro/', UserRegistrationView.as_view()),

    # LOGIN (SÓ UM PADRÃO)
    path('api/login/', LoginView.as_view(), name='login'),

    # API PRINCIPAL
    path('api/', include(router.urls)),

    # UPLOADS
    path('api/media/', include(uploader_router.urls)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
