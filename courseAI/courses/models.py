from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Project(models.Model):
    """Programming project for interactive lessons."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Link to the generated lesson that created this project
    lesson = models.OneToOneField('generation.GeneratedLesson', on_delete=models.CASCADE, related_name='programming_project', null=True, blank=True)
    
    # Grading methodology
    GRADING_CHOICES = [
        ('ai_review', 'AI Review'),
        ('terminal_matching', 'Terminal Matching'),
    ]
    grading_method = models.CharField(max_length=20, choices=GRADING_CHOICES, default='ai_review')
    
    # Expected output for terminal matching
    expected_output = models.TextField(blank=True, help_text="Expected terminal output for grading")
    
    is_final_project = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

class File(models.Model):
    project = models.ForeignKey(Project, related_name='files', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    relative_path = models.CharField(max_length=500)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['project', 'relative_path']

    def __str__(self):
        return f"{self.project.name}/{self.relative_path}"

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructor = models.CharField(max_length=100)
    duration = models.IntegerField(help_text="Duration in hours")
    current = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class Chapter(models.Model):
    course = models.ForeignKey(Course, related_name='chapters', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()

    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
class Lesson(models.Model):
    chapter = models.ForeignKey(Chapter, related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    video_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.chapter.title} - {self.title}"