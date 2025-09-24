from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    #name = models.CharField(max_length=50, null=True, blank=True)
    username = None
    email = models.EmailField(unique=True)

    nickname = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    oauth_id = models.CharField(max_length=100, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []