from rest_framework.routers import DefaultRouter

from posts.views import PostViewSet

router = DefaultRouter()
router.register("posts", PostViewSet)

urlpatterns = router.urls
