from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from .models import Article
from .serializers import ArticleSerializer

class ArticleViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Article.objects.none()
        
        return Article.objects.filter(user=self.request.user).order_by("-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content", "author", "journal", "created_at"] #/article/?search=django
    ordering_fields = ["created_at", "title", "journal", "id"] #/article/?ordering=title #/article/?ordering=-journal
    ordering = ["-created_at"]