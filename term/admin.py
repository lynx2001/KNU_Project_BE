from django.contrib import admin
from .models import Term

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("term", "meaning")
    search_fields = ("term", "meaning")
    #list_filter = ("journal",)
    #ordering = ("-created_at",)