from django.urls import path
from . import views

app_name = 'generation'

urlpatterns = [
    path('', views.generation_form, name='generation_form'),
    path('submit/', views.process_generation, name='process_generation'),
    path('courses/', views.course_list, name='course_list'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('quiz/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('lesson/<int:lesson_id>/youtube/', views.lesson_youtube, name='lesson_youtube'),
    path('lesson/<int:lesson_id>/article/', views.lesson_article, name='lesson_article'),
    path('lesson/<int:lesson_id>/external/', views.lesson_external, name='lesson_external'),
    path('lesson/<int:lesson_id>/text/', views.lesson_text_response, name='lesson_text_response'),
    path('lesson/<int:lesson_id>/text/submit/', views.submit_text_responses, name='submit_text_responses'),
    path('lesson/<int:lesson_id>/project/', views.load_lesson_project, name='load_lesson_project'),
    path('lesson/<int:lesson_id>/correct/', views.submit_code_correction, name='submit_code_correction'),
    path('api/ai-feedback/', views.get_ai_feedback, name='get_ai_feedback'),
]