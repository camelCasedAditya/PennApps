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