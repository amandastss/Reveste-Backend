from django.urls import path

from core.views.login import LoginView

urlpatterns = [
    path('login/', LoginView.as_view()),
]
