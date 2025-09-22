from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from .models import Article
from .serializers import ArticleSerializer

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content", "author", "journal", "url"]
    ordering_fields = ["created_at", "title", "journal", "id"]
    ordering = ["-created_at"]