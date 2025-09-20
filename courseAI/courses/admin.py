from django.contrib import admin
from .models import Course, Chapter, Lesson, Project, File

# Register your models here.
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description']

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['project', 'name', 'relative_path', 'updated_at']
    list_filter = ['project', 'updated_at']
    search_fields = ['name', 'relative_path', 'project__name']

admin.site.register(Course)
admin.site.register(Chapter) 
admin.site.register(Lesson)
