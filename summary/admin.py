from django.contrib import admin
from .models import Summary, SummaryGroup


@admin.register(SummaryGroup)
class SummaryGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "group_index", "created_at")
    ordering = ("-date", "group_index")

@admin.register(Summary)
class SummaryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "group", "article")
    search_fields = ("title", "content")
    fields = ("title", "content", "article", "group", "terms")