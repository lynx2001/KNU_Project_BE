from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from .models import Term
from .serializers import TermSerializer

class TermViewSet(viewsets.ModelViewSet):
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["term", "meaning"]
