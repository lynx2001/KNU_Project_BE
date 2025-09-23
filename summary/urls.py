from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SummaryViewSet

router = DefaultRouter()
router.register(r"summary", SummaryViewSet, basename="summary")

urlpatterns = [ path("", include(router.urls)), ]