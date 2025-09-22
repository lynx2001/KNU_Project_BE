from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=200, null=False)
    content = models.TextField(null=True, blank=True)
    author = models.CharField(max_length=20)
    url = models.CharField(max=255)
    journal = models.CharField(max=50)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "article"

    def __str__(self):
        return self.title