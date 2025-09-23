from django.db import models

class Quiz(models.Model):
    #id = models.BigAutoField(primary_key=True)
    question = models.TextField(null=False, blank=False)
    answer = models.TextField(null=False, blank=False)
    ox = models.BooleanField()

    class Meta:
        db_table = "quiz"

    def __str__(self):
        return self.question