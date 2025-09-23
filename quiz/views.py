from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from .models import Quiz
from .serializers import QuizSerializer

class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["question", "answer", "ox"]
    #ordering_fields = ["created_at", "title", "journal", "id"]
    #ordering = ["-created_at"]