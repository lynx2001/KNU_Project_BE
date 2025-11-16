from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QnAViewSet

router = DefaultRouter()
router.register(r"qna", QnAViewSet, basename="qna")

urlpatterns = [ path("", include(router.urls)), ]