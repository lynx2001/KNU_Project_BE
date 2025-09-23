from django.db import models

class Term(models.Model):
    #id = models.BigAutoField(primary_key=True)
    term = models.CharField(max_length=200, null=False)
    meaning = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "term"

    def __str__(self):
        return self.term