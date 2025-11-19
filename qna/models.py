from django.db import models
from django.conf import settings

class QnA(models.Model):
    #id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="qnas",
        null=True, blank=True # 임시 !!! 지우자
    )
    question = models.TextField(null=False, help_text="사용자 질문")
    answer = models.TextField(null=True, blank=True, help_text="AI 답변")

    class Meta:
        db_table = "qna"

    def __str__(self):
        return self.answer