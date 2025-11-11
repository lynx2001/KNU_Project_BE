from django.db import models
from summary.models import Summary
from django.contrib.auth.models import User

class Quiz(models.Model):
    #id = models.BigAutoField(primary_key=True)
    # 문제 난이도(사용자 등급에 따른) / 문제 해설 / 중복 여부
    TYPE_OX = "OX"
    TYPE_MC3 = "MC3"
    TYPE_MC5 = "MC5"
    TYPE_SC = "SC"
    TYPE_CHOICES = [
        (TYPE_OX, "OX"),
        (TYPE_MC3, "Multiple Choice (3)"),
        (TYPE_MC5, "Multiple Choice (5)"),
        (TYPE_SC, "Short Answer"),
    ]

    summary = models.ForeignKey(
        Summary,
        on_delete=models.CASCADE,
        related_name="quizzes",
        null=True, # 임시 !!! (지우자)
        blank=True, # 임시 !!! (지우자)
    )

    quiz_type = models.CharField(
        max_length=4,
        choices=TYPE_CHOICES,
        default=TYPE_OX,
    )

    # 공통
    question = models.TextField()
    explanation = models.TextField(blank=True)

    correct_bool = models.BooleanField(
        null=True, blank=True,
        help_text="OX 문제일 때만 사용 (O=True, X=False)"
    )

    correct_text = models.CharField(
        max_length=255, blank=True,
        help_text="객관식/단답형 문제일 때만 사용"
    )


    class Meta:
        db_table = "quiz"

    def __str__(self):
        return f"[{self.quiz_type}] {self.question[:40]}"
    
    @property
    def is_ox(self):
        return self.quiz_type == self.TYPE_OX
    
    @property
    def is_mc3(self):
        return self.quiz_type == self.TYPE_MC3
    
    @property
    def is_mc5(self):
        return self.quiz_type == self.TYPE_MC5
    
    @property
    def is_sc(self):
        return self.quiz_type == self.TYPE_SC
    
class QuizOption(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="options",
    )
    order = models.PositiveSmallIntegerField(default=1)
    text = models.CharField(max_length=255)

    class Meta:
        db_table = "quiz_option"
        ordering = ["order"]

    def __str__(self):
        return f"{self.quiz.pk} - {self.text}"
    

class UserQuizAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)

    # OX형
    ox_answer = models.BooleanField(
        null=True,
        blank=True,
        help_text="OX 문제에서 사용"
    )

    # 객관식(MC3, MC5)
    selected_option = models.ForeignKey(
        QuizOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # 단답형(SC)
    text_answer = models.CharField(
        max_length=255,
        blank=True,
        help_text="단답형 문제에서 사용"
    )

    is_correct = models.BooleanField()

    class Meta:
        db_table = "user_quiz_answer"
        unique_together = ("user", "quiz")

    def __str__(self):
        return f"{self.user} - {self.quiz.pk} - {self.is_correct}"


