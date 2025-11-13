from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SummaryViewSet, SummaryGroupViewSet

router = DefaultRouter()
router.register(r"summary", SummaryViewSet, basename="summary")
router.register(r"summary-group", SummaryGroupViewSet, basename="summary-group")

urlpatterns = [ path("", include(router.urls)), ]