from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from core.views.login import LoginView
from .views import HistoricoPesquisaViewSet

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
