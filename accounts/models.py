from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    nickname = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    score = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.nickname or self.user.username
    
    @property
    def grade(self):
        if self.score >= 10000:
            return "숲"
        elif self.score >= 4000:
            return "나무"
        elif self.score >= 1000:
            return "새싹"
        elif self.score > 0:
            return "씨앗"
        else:
            return None
    
        
    def is_seed(self):
        return (self.score > 0 and self.score < 1000)

    def is_sprout(self):
        return (self.score >= 1000 and self.score < 4000)

    def is_tree(self):
        return (self.score >= 4000 and self.score < 10000)

    def is_forest(self):
        return self.score >= 10000