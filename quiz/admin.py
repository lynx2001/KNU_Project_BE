from django.contrib import admin
from .models import Quiz, QuizOption, UserQuizAnswer


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "summary",
        "quiz_type",
        "short_question",
    )
    list_filter = ("quiz_type", "summary")
    search_fields = ("question",)

    def short_question(self, obj):
        return (obj.question[:40] + "...") if len(obj.question) > 40 else obj.question
    short_question.short_description = "Question"


@admin.register(QuizOption)
class QuizOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "text", "order")
    list_filter = ("quiz",)
    search_fields = ("text",)


@admin.register(UserQuizAnswer)
class UserQuizAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "quiz",
        "display_answer",
        "is_correct",
    )
    list_filter = ("is_correct",)
    search_fields = ("user__username", "quiz__question")

    def display_answer(self, obj):
        if obj.quiz.is_ox:
            return f"OX: {obj.ox_answer}"
        if obj.quiz.is_mc3 or obj.quiz.is_mc5:
            return f"MC: {obj.selected_option}"
        if obj.quiz.is_sc:
            return f"SC: {obj.text_answer}"
        return "-"
    display_answer.short_description = "Answer"
