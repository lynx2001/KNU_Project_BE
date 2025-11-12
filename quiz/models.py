# quiz/models.py

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from summary.models import Summary


# 1. 모든 퀴즈의 공통 부분을 담는 추상 기본 모델
class BaseQuiz(models.Model):
    summary = models.ForeignKey(
        Summary,
        on_delete=models.CASCADE,
        related_name="%(class)s_quizzes", # OXQuiz -> summary.oxquiz_quizzes
        # ShortAnswerQuiz -> summary.shortanswerquiz_quizzes
        # MultipleChoiceQuiz -> summary.multiplechoicequiz_quizzes
        null=True, # 임시 !!! (지우자)
        blank=True, # 임시 !!! (지우자)
    )
    question = models.TextField()
    explanation = models.TextField(blank=True)

    class Meta:
        abstract = True # 이 모델은 DB 테이블로 만들어지지 않습니다.

    def __str__(self):
        return self.question[:50]


# 2. 유형별 실제 모델들
class OXQuiz(BaseQuiz):
    correct_answer = models.BooleanField(help_text="O=True, X=False")

    class Meta:
        db_table = "quiz_ox"

    def __str__(self):
        return f"[OX] {self.question[:40]}"


class ShortAnswerQuiz(BaseQuiz):
    correct_answer = models.CharField(max_length=255)

    class Meta:
        db_table = "quiz_short_answer"

    def __str__(self):
        return f"[단답형] {self.question[:40]}"


class MultipleChoiceQuiz(BaseQuiz):
    TYPE_MC3 = 3
    TYPE_MC5 = 5
    TYPE_CHOICES = [
        (TYPE_MC3, "Multiple Choice (3)"),
        (TYPE_MC5, "Multiple Choice (5)"),
    ]
    choice_type = models.PositiveSmallIntegerField(
        choices=TYPE_CHOICES,
        default=TYPE_MC3
    )

    class Meta:
        db_table = "quiz_multiple_choice"

    def __str__(self):
        return f"[객관식-{self.choice_type}] {self.question[:40]}"


class QuizOption(models.Model):
    quiz = models.ForeignKey(
        MultipleChoiceQuiz, # 이제 객관식 퀴즈만 참조합니다.
        on_delete=models.CASCADE,
        related_name="options",
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False) # 정답 여부를 여기에 저장합니다.
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "quiz_option"
        ordering = ["order"]

    def __str__(self):
        return f"{self.quiz.pk} - {self.text}"


class UserQuizAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # GenericForeignKey를 사용하여 모든 종류의 퀴즈 모델을 참조합니다.
    content_type = models.ForeignKey(ContentType, 
                                     on_delete=models.CASCADE,
                                     limit_choices_to=Q(app_label='quiz', model='oxquiz') | 
                                                        Q(app_label='quiz', model='multiplechoicequiz') |
                                                        Q(app_label='quiz', model='shortanswerquiz'),
                                    )
    object_id = models.PositiveIntegerField()
    quiz = GenericForeignKey('content_type', 'object_id')

    # 답변 필드들
    ox_answer = models.BooleanField(null=True, blank=True)
    selected_option = models.ForeignKey(QuizOption, on_delete=models.SET_NULL, null=True, blank=True)
    text_answer = models.CharField(max_length=255, blank=True)

    is_correct = models.BooleanField()

    class Meta:
        db_table = "user_quiz_answer"
        # 한 사용자는 특정 퀴즈(어떤 타입이든)에 대해 하나의 답변만 가집니다.
        unique_together = ("user", "content_type", "object_id")

    def __str__(self):
        return f"{self.user} - {self.quiz} - {'Correct' if self.is_correct else 'Incorrect'}"