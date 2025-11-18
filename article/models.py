from django.db import models
from django.conf import settings

class Article(models.Model):
    # rss - 부가정보 (parsing 부담 줄이기)
    #id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="articles",
        null=True, blank=True # 임시 !!! 지우자
    )
    title = models.CharField(max_length=200, null=False)
    content = models.TextField(null=True, blank=True)
    author = models.CharField(max_length=20) 
    url = models.URLField(null=True,blank=True)
    journal = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "article"

    def __str__(self):
        return self.title