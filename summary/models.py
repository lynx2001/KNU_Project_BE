from django.db import models
from article.models import Article

class SummaryGroup(models.Model):
    date = models.DateField()
    group_index = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

class Summary(models.Model):
    #id = models.BigAutoField(primary_key=True)
    # 신문 원문 요약 날짜 추가
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="summaries",
        null=True, # 임시 !!! (지우자)
        blank=True, # 임시 !!! (지우자)
    )
    title = models.CharField(max_length=200, null=True)
    content = models.TextField(null=True, blank=True)
    group = models.ForeignKey(
        'SummaryGroup',
        on_delete=models.CASCADE,
        related_name="summaries",
        null=True, # 임시 !!! (지우자)
        blank=True, # 임시 !!! (지우자)
    )

    class Meta:
        db_table = "summary"

    def __str__(self):
        return f"[{self.title}] {self.title}"