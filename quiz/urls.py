from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OXQuizViewSet, ShortAnswerQuizViewSet, MultipleChoiceQuizViewSet,
    QuizCreateAPIView,
    QuizBulkCreateAPIView, # (new) [신규 import]
    QuizSubmitAPIView, # (new) [신규 import]
)

router = DefaultRouter()
router.register('ox-quiz', OXQuizViewSet)
router.register('sc-quiz', ShortAnswerQuizViewSet)
router.register('mc-quiz', MultipleChoiceQuizViewSet)

urlpatterns = [
    path("", include(router.urls)), 
    path("quiz/", QuizCreateAPIView.as_view(), name="quiz-create"), #기존 1개 퀴즈 생성
    # 2개 생성 url 추가
    path("quiz/bulk-create/", QuizBulkCreateAPIView.as_view(), name="quiz-bulk-create"),
    # 퀴즈 채점 및 점수반영 url 추가
    # content_type_id : 퀴즈유형(OX, MC, SC) / object_id : 퀴즈ID(PK)
    path("quiz/submit/<int:content_type_id>/<int:object_id>/", QuizSubmitAPIView.as_view(), name="quiz-submit"),
 ]