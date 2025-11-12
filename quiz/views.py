# quiz/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import OXQuiz, ShortAnswerQuiz, MultipleChoiceQuiz
from .serializers import (
    OXQuizSerializer, ShortAnswerQuizSerializer, MultipleChoiceQuizSerializer,
    QuizCreateSerializer
)

# --- 유형별 조회/수정/삭제 ViewSets ---

class OXQuizViewSet(viewsets.ModelViewSet):
    queryset = OXQuiz.objects.all()
    serializer_class = OXQuizSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ShortAnswerQuizViewSet(viewsets.ModelViewSet):
    queryset = ShortAnswerQuiz.objects.all()
    serializer_class = ShortAnswerQuizSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class MultipleChoiceQuizViewSet(viewsets.ModelViewSet):
    queryset = MultipleChoiceQuiz.objects.all()
    serializer_class = MultipleChoiceQuizSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --- 통합 퀴즈 생성 API View ---

class QuizCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated] # 생성은 로그인한 사용자만

    def post(self, request, *args, **kwargs):
        """
        모든 유형의 퀴즈를 이 엔드포인트에서 생성합니다.
        request body에 "quiz_type" 필드 (OX, SC, MC3, MC5)가 필수입니다.
        """
        serializer = QuizCreateSerializer(data=request.data)
        if serializer.is_valid():
            quiz_instance = serializer.save()
            
            # 생성된 객체의 유형에 맞는 시리얼라이저로 응답 데이터를 만듭니다.
            if isinstance(quiz_instance, OXQuiz):
                response_serializer = OXQuizSerializer(quiz_instance)
            elif isinstance(quiz_instance, ShortAnswerQuiz):
                response_serializer = ShortAnswerQuizSerializer(quiz_instance)
            elif isinstance(quiz_instance, MultipleChoiceQuiz):
                response_serializer = MultipleChoiceQuizSerializer(quiz_instance)
            else:
                return Response({"error": "Unknown quiz type created"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)