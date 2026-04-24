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
    SessaoLoginViewSet,
    UserRegistrationView,
    UserViewSet,
    VendaViewSet,
)
from core.views.sessaoLogin import SessaoLoginViewSet  # noqa: F811
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
router.register(r'sessao-login', SessaoLoginViewSet, basename='sessao-login')

urlpatterns = [
    path('admin/', admin.site.urls),
    # OpenAPI 3
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/doc/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
    # Autenticação JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # Registro de usuários
    path('api/registro/', UserRegistrationView.as_view(), name='user_registration'),
    # API
    path('api/', include(router.urls)),
    path('api/media/', include(uploader_router.urls)),
]

urlpatterns += static(settings.MEDIA_ENDPOINT, document_root=settings.MEDIA_ROOT)
