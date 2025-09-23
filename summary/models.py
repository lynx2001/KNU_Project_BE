from django.db import models

class Summary(models.Model):
    #id = models.BigAutoField(primary_key=True)
    article_id = models.IntegerField(null=False)
    title = models.CharField(max_length=200, null=True)
    content = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "summary"

    def __str__(self):
        return self.title