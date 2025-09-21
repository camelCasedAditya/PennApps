from django.db import models
from django.contrib.auth.models import User
import json

class CourseGeneration(models.Model):
    """Main course generation record."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    user_prompt = models.TextField(help_text="Original user prompt for course generation", default="")
    experience_level = models.CharField(max_length=500, default="Beginner")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_chapters = models.IntegerField(default=0)
    total_lessons = models.IntegerField(default=0)
    
    # Store the complete course data as JSON
    course_data_json = models.JSONField(null=True, blank=True, help_text="Complete course structure as JSON")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Optional user association
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Course: {self.user_prompt[:50]}... ({self.status})"

class GeneratedChapter(models.Model):
    """Individual chapters within a course."""
    course_generation = models.ForeignKey(CourseGeneration, on_delete=models.CASCADE, related_name='chapters')
    
    chapter_number = models.IntegerField()
    chapter_name = models.CharField(max_length=200)
    chapter_description = models.TextField()
    difficulty_rating = models.IntegerField(help_text="Difficulty from 1-10", default=-1)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['chapter_number']
        unique_together = ['course_generation', 'chapter_number']
        
    def __str__(self):
        return f"Ch.{self.chapter_number}: {self.chapter_name}"

class LessonType(models.Model):
    """Types of lessons available."""
    name = models.CharField(max_length=50, unique=True)  # e.g., 'vid', 'txt', 'mcq'
    type_id = models.IntegerField(unique=True)  # 1, 2, 3, etc.
    display_name = models.CharField(max_length=100, default="")  # e.g., 'Video', 'Text Response'
    description = models.TextField(blank=True)

    complete = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['type_id']
        
    def __str__(self):
        return f"{self.display_name} ({self.name})"

class GeneratedLesson(models.Model):
    """Individual lessons within chapters."""
    chapter = models.ForeignKey(GeneratedChapter, on_delete=models.CASCADE, related_name='lessons')
    
    lesson_number = models.IntegerField()
    lesson_type = models.CharField(max_length=50)  # vid, txt, mcq, etc.
    lesson_type_id = models.IntegerField(null=True, blank=True)
    lesson_name = models.CharField(max_length=200)
    lesson_description = models.TextField()
    lesson_details = models.TextField()
    lesson_goals = models.TextField(help_text="Learning objectives")
    lesson_guidelines = models.TextField(help_text="Guidelines for creating the lesson", blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['lesson_number']
        unique_together = ['chapter', 'lesson_number']
        
    def __str__(self):
        return f"L{self.lesson_number}: {self.lesson_name}"

class GenerationLog(models.Model):
    """Logs for tracking generation process."""
    LOG_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('debug', 'Debug'),
    ]
    
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    course_generation = models.ForeignKey(CourseGeneration, on_delete=models.CASCADE, related_name='logs')
    step = models.CharField(max_length=100, help_text="Which step in the generation process")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    level = models.CharField(max_length=10, choices=LOG_LEVELS, default='info')
    message = models.TextField()
    
    # Optional data storage
    data = models.JSONField(null=True, blank=True, help_text="Additional data for this log entry")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.step} - {self.status} ({self.level})"

class MultipleChoiceQuiz(models.Model):
    """Multiple choice quiz for a lesson."""
    lesson = models.OneToOneField(GeneratedLesson, on_delete=models.CASCADE, related_name='quiz')
    
    # Store quiz data as JSON
    quiz_data = models.JSONField(help_text="Quiz questions, options, and answers in JSON format")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Quiz for {self.lesson.lesson_name}"

class QuizAttempt(models.Model):
    """Store user attempts at completing a multiple choice quiz."""
    quiz = models.ForeignKey(MultipleChoiceQuiz, on_delete=models.CASCADE, related_name='attempts')
    
    # Store user answers as JSON
    user_answers = models.JSONField(help_text="User's answers to quiz questions in JSON format")
    
    # Store results as JSON (correct/incorrect for each question)
    results = models.JSONField(help_text="Results showing which answers were correct/incorrect")
    
    # Overall score
    score = models.IntegerField(help_text="Number of correct answers")
    total_questions = models.IntegerField(help_text="Total number of questions")
    
    # Optional user association
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Quiz attempt for {self.quiz.lesson.lesson_name} - Score: {self.score}/{self.total_questions}"
    
class ArticleContent(models.Model):
    """Store generated article content for text-based lessons."""
    lesson = models.OneToOneField(GeneratedLesson, on_delete=models.CASCADE, related_name='article')
    
    # Store article content
    content = models.TextField(help_text="Generated article content")
    
    def __str__(self):
        return f"Article for {self.lesson.lesson_name}"

class YouTubeVideo(models.Model):
    """Store YouTube video info for a lesson."""
    lesson = models.ForeignKey(GeneratedLesson, on_delete=models.CASCADE, related_name='youtube_videos')
    video_id = models.CharField(max_length=50)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    channel_title = models.CharField(max_length=200, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    video_url = models.URLField(blank=True)
    # Store the full API response for flexibility
    raw_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"YouTube: {self.title} ({self.video_id})"

class Project(models.Model):
    """Programming project for interactive lessons."""
    lesson = models.OneToOneField(GeneratedLesson, on_delete=models.CASCADE, related_name='project')
    
    # Starter code files as JSON (filename -> code)
    starter_files = models.JSONField(help_text="Dictionary of filename to starter code content")
    
    # Grading methodology
    GRADING_CHOICES = [
        ('ai_review', 'AI Review'),
        ('terminal_matching', 'Terminal Matching'),
    ]
    grading_method = models.CharField(max_length=20, choices=GRADING_CHOICES, default='ai_review')
    
    # Expected output for terminal matching
    expected_output = models.TextField(blank=True, help_text="Expected terminal output for grading")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Project for {self.lesson.lesson_name}"

class ExternalArticles(models.Model):
    """Store external article URLs for text-based lessons."""
    lesson = models.OneToOneField(GeneratedLesson, on_delete=models.CASCADE, related_name='external_article')
    
    # Store article URL instead of content
    url = models.URLField(help_text="URL of the external article")
    
    def __str__(self):
        return f"External Article for {self.lesson.lesson_name}"


class TextResponseQuestion(models.Model):
    """Store individual text response questions for lessons."""
    lesson = models.ForeignKey(GeneratedLesson, on_delete=models.CASCADE, related_name='text_response_questions')
    
    question_number = models.IntegerField(help_text="Question number within the lesson")
    question = models.TextField(help_text="The question text")
    optimal_answer = models.TextField(help_text="The optimal answer for this question")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['question_number']
        unique_together = ['lesson', 'question_number']
        
    def __str__(self):
        return f"Q{self.question_number}: {self.question[:50]}..."


class TextResponseSubmission(models.Model):
    """Store user submissions for text response questions and their grades."""
    lesson = models.ForeignKey(GeneratedLesson, on_delete=models.CASCADE, related_name='text_submissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Store all answers as JSON (question_number -> user_answer)
    user_answers = models.JSONField(help_text="User's answers to all questions in JSON format")
    
    # Store grades as JSON (question_number -> grade_data)
    grades = models.JSONField(help_text="Grades and feedback for each question in JSON format")
    
    # Overall scoring
    total_score = models.FloatField(help_text="Overall score as percentage (0-100)")
    total_questions = models.IntegerField(help_text="Total number of questions answered")
    
    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
        
    def __str__(self):
        return f"Submission for {self.lesson.lesson_name} - Score: {self.total_score:.1f}%"