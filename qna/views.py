from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from .models import QnA
from accounts.models import Profile
from .serializers import QnASerializer
from rest_framework.exceptions import PermissionDenied

from multiAgent.services import run_agent

class QnAViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return QnA.objects.none()
        
        return QnA.objects.filter(user=user).order_by("-id")

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied("로그인한 사용자만 QnA를 작성할 수 있습니다.")
        serializer.save(user=user)

        question_text = serializer.validated_data.get('question')
        ai_answer = run_agent(user, question_text)

        serializer.save(user=user, answer=ai_answer)

    queryset = QnA.objects.all()
    serializer_class = QnASerializer

    # 배포용
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    # 개발용
    #permission_classes = [permissions.AllowAny]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["id", "question", "answer"]
    ordering_fields = ["id", "question", "answer"]
    ordering = ["id"]