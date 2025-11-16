from django.db import models

class QnA(models.Model):
    #id = models.BigAutoField(primary_key=True)
    question = models.TextField(null=False)
    answer = models.TextField(null=True, blank=True)
    

    class Meta:
        db_table = "qna"

    def __str__(self):
        return self.answer