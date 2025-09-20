from django.urls import path
from . import views

app_name = 'generation'

urlpatterns = [
    path('', views.generation_form, name='generation_form'),
    path('submit/', views.process_generation, name='process_generation'),
]