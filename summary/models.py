from django.db import models
from article.models import Article
from term.models import Term  # 1. Term 모델 추가

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
    terms = models.ManyToManyField(
        Term,
        related_name="summaries",  # Term 입장에서 .summaries로 Summary 목록을 가져올 수 있습니다.
        blank=True                 # 요약에 연결된 용어가 없을 수도 있습니다.
    )

    class Meta:
        db_table = "summary"

    def __str__(self):
        return f"[{self.title}] {self.title}"