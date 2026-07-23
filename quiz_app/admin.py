"""Admin configuration for quizzes and their questions."""

from django.contrib import admin

from quiz_app.models import Quiz, Question


class QuestionInline(admin.TabularInline):
    """Edit a quiz's questions directly inside the quiz form."""

    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Manage quizzes together with their questions."""

    list_display = ["title", "owner", "created_at"]
    list_filter = ["created_at", "owner"]
    search_fields = ["title", "description"]
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Manage single questions independently of their quiz."""

    list_display = ["question_title", "quiz", "answer"]
    list_filter = ["quiz"]
    search_fields = ["question_title"]
