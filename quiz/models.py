from django.db import models

class Quiz(models.Model):
    #id = models.BigAutoField(primary_key=True)
    # 문제 난이도(사용자 등급에 따른) / 문제 해설 / 중복 여부
    question = models.TextField(null=False, blank=False)
    answer = models.TextField(null=False, blank=False)
    ox = models.BooleanField()

    class Meta:
        db_table = "quiz"

    def __str__(self):
        return self.question