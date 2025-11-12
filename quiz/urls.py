from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OXQuizViewSet, ShortAnswerQuizViewSet, MultipleChoiceQuizViewSet, QuizCreateAPIView

router = DefaultRouter()
router.register('ox-quiz', OXQuizViewSet)
router.register('sc-quiz', ShortAnswerQuizViewSet)
router.register('mc-quiz', MultipleChoiceQuizViewSet)

urlpatterns = [path("", include(router.urls)), 
               path("quiz/", QuizCreateAPIView.as_view(), name="quiz-create"),]