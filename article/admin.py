from django.contrib import admin
from .models import Article

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "journal", "created_at")
    search_fields = ("title", "content", "author", "journal", "url")
    list_filter = ("journal",)
    ordering = ("-created_at",)