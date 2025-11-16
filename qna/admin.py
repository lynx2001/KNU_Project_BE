from django.contrib import admin
from .models import QnA

# Register your models here.
@admin.register(QnA)
class QnAAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "answer")
    search_fields = ("id", "question", "answer")
    list_filter = ("question", "answer",)
    ordering = ("id",)