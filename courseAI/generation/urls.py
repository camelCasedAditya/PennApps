from django.urls import path
from . import views

app_name = 'generation'

urlpatterns = [
    path('', views.generation_form, name='generation_form'),
    path('submit/', views.process_generation, name='process_generation'),
    path('quiz/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('lesson/<int:lesson_id>/youtube/', views.lesson_youtube, name='lesson_youtube'),
]