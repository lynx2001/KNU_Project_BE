from django.contrib import admin
from .models import Quiz

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "answer", "ox")
    search_fields = ("id", "question", "answer", "ox")
    #list_filter = ("journal",)
    #ordering = ("-created_at",)