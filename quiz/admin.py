# quiz/admin.py

from django.contrib import admin
from .models import (
    OXQuiz, ShortAnswerQuiz, MultipleChoiceQuiz, QuizOption, UserQuizAnswer
)

# --- 객관식 퀴즈 Admin에서 보기(Option)를 함께 편집하기 위한 Inline 설정 ---
class QuizOptionInline(admin.TabularInline):
    model = QuizOption
    extra = 3  # 기본으로 3개의 보기 입력 필드를 보여줌
    ordering = ["order"]


# --- 모든 퀴즈 Admin 클래스의 공통 부분을 정의하는 기본 클래스 ---
@admin.register(MultipleChoiceQuiz)
class MultipleChoiceQuizAdmin(admin.ModelAdmin):
    list_display = ("id", "summary", "question_summary", "choice_type")
    list_filter = ("summary", "choice_type")
    search_fields = ("question",)
    inlines = [QuizOptionInline] # 객관식 퀴즈 편집 페이지에만 Inline 추가

    def question_summary(self, obj):
        return (obj.question[:40] + "...") if len(obj.question) > 40 else obj.question
    question_summary.short_description = "Question"


@admin.register(OXQuiz)
class OXQuizAdmin(admin.ModelAdmin):
    list_display = ("id", "summary", "question_summary", "correct_answer")
    list_filter = ("summary",)
    search_fields = ("question",)

    def question_summary(self, obj):
        return (obj.question[:40] + "...") if len(obj.question) > 40 else obj.question
    question_summary.short_description = "Question"


@admin.register(ShortAnswerQuiz)
class ShortAnswerQuizAdmin(admin.ModelAdmin):
    list_display = ("id", "summary", "question_summary", "correct_answer")
    list_filter = ("summary",)
    search_fields = ("question",)

    def question_summary(self, obj):
        return (obj.question[:40] + "...") if len(obj.question) > 40 else obj.question
    question_summary.short_description = "Question"


# --- QuizOption은 직접적인 관리 필요성이 낮아졌지만, 필요하다면 등록 ---
@admin.register(QuizOption)
class QuizOptionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "text", "is_correct", "order")
    list_filter = ("quiz", "is_correct")
    search_fields = ("text",)


# --- UserQuizAnswer Admin 설정 ---
@admin.register(UserQuizAnswer)
class UserQuizAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "related_quiz", # quiz 필드 대신 표시할 메서드
        "display_answer",
        "is_correct",
    )
    list_filter = ("is_correct", "content_type") # 어떤 유형의 퀴즈인지 필터링
    search_fields = ("user__username",)
    
    # GenericForeignKey 필드는 직접 검색을 지원하지 않으므로 search_fields에서 제외합니다.
    # 꼭 필요하다면 별도의 커스터마이징이 필요합니다.

    def related_quiz(self, obj):
        # 연결된 퀴즈 객체를 반환합니다.
        return obj.quiz
    related_quiz.short_description = "Quiz"

    def display_answer(self, obj):
        # content_type을 확인하여 어떤 종류의 퀴즈인지 판단합니다.
        model_name = obj.content_type.model
        if model_name == 'oxquiz':
            return f"OX: {obj.ox_answer}"
        elif model_name == 'multiplechoicequiz':
            option_text = obj.selected_option.text if obj.selected_option else "N/A"
            return f"MC: {option_text}"
        elif model_name == 'shortanswerquiz':
            return f"SC: {obj.text_answer}"
        return "-"
    display_answer.short_description = "Submitted Answer"