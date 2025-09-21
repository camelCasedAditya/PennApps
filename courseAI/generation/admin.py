from django.contrib import admin
from .models import CourseGeneration, GeneratedChapter, GeneratedLesson, LessonType, GenerationLog, MultipleChoiceQuiz, ArticleContent, YouTubeVideo, ExternalArticles, TextResponseQuestion, TextResponseSubmission


@admin.register(CourseGeneration)
class CourseGenerationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_prompt_short', 'experience_level', 'total_chapters', 'total_lessons', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'experience_level']
    search_fields = ['user_prompt', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'total_chapters', 'total_lessons']
    
    def user_prompt_short(self, obj):
        return obj.user_prompt[:100] + "..." if len(obj.user_prompt) > 100 else obj.user_prompt
    user_prompt_short.short_description = 'User Prompt'


@admin.register(GeneratedChapter)
class GeneratedChapterAdmin(admin.ModelAdmin):
    list_display = ['id', 'course_generation', 'chapter_number', 'chapter_name', 'difficulty_rating', 'lesson_count']
    list_filter = ['difficulty_rating', 'created_at']
    search_fields = ['chapter_name', 'chapter_description', 'course_generation__user_prompt']
    readonly_fields = ['created_at']
    ordering = ['course_generation', 'chapter_number']
    
    def lesson_count(self, obj):
        return obj.lessons.count()
    lesson_count.short_description = 'Number of Lessons'


@admin.register(GeneratedLesson)
class GeneratedLessonAdmin(admin.ModelAdmin):
    list_display = ['id', 'lesson_name', 'lesson_type', 'chapter', 'lesson_number']
    list_filter = ['lesson_type', 'created_at']
    search_fields = ['lesson_name', 'lesson_description', 'chapter__chapter_name']
    readonly_fields = ['created_at']
    ordering = ['chapter__course_generation', 'chapter__chapter_number', 'lesson_number']


@admin.register(LessonType)
class LessonTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'display_name', 'type_id', 'description']
    list_filter = ['type_id']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['type_id']


@admin.register(GenerationLog)
class GenerationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'course_generation', 'step', 'status', 'created_at']
    list_filter = ['status', 'step', 'created_at']
    search_fields = ['step', 'message', 'course_generation__project_description']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

admin.site.register(MultipleChoiceQuiz)
admin.site.register(ArticleContent)
admin.site.register(YouTubeVideo)
admin.site.register(ExternalArticles)


@admin.register(TextResponseQuestion)
class TextResponseQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'lesson', 'question_number', 'question_preview', 'created_at']
    list_filter = ['lesson__lesson_type', 'question_number', 'created_at']
    search_fields = ['question', 'optimal_answer', 'lesson__lesson_name']
    readonly_fields = ['created_at']
    ordering = ['lesson__chapter__course_generation', 'lesson__chapter__chapter_number', 'lesson__lesson_number', 'question_number']
    
    def question_preview(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
    question_preview.short_description = 'Question Preview'


@admin.register(TextResponseSubmission)
class TextResponseSubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'lesson', 'user', 'total_score', 'total_questions', 'submitted_at', 'graded_at']
    list_filter = ['submitted_at', 'graded_at', 'lesson__lesson_type', 'total_score']
    search_fields = ['lesson__lesson_name', 'user__username']
    readonly_fields = ['submitted_at', 'graded_at']
    ordering = ['-submitted_at']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ['lesson', 'user', 'user_answers']
        return self.readonly_fields