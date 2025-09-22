from django.db import models

class Article(models.Model):
    #id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=200, null=False)
    content = models.TextField(null=True, blank=True)
    author = models.CharField(max_length=20)
    url = models.CharField(max_length=255, null=True)
    journal = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "article"

    def __str__(self):
        return self.title