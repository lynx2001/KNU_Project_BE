from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from .models import Article, Summary, SummaryGroup
from .serializers import SummarySerializer, SummaryGroupSerializer
from django.utils import timezone
from django.db.models import Max

class SummaryViewSet(viewsets.ModelViewSet):
    queryset = Summary.objects.all()
    serializer_class = SummarySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content"]
    ordering_fields = ["title", "id"]


class SummaryGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SummaryGroup.objects.prefetch_related('summaries__article').all()

    serializer_class = SummaryGroupSerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [filters.OrderingFilter]
    search_fields = ["date", "group_index"]
    ordering_fields = ["date", "group_index"]
    ordering = ["-date", "-group_index"]