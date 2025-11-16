from django.shortcuts import render

from rest_framework import viewsets, permissions, filters
from .models import QnA
from .serializers import QnASerializer

class QnAViewSet(viewsets.ModelViewSet):
    queryset = QnA.objects.all()
    serializer_class = QnASerializer
    #permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    permission_classes = [permissions.AllowAny]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["id", "question", "answer"]
    ordering_fields = ["id", "question", "answer"]
    ordering = ["id"]