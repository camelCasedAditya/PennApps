from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.HomePageView.as_view(), name='homepage'),
    # Alternative function-based view
    # path('', views.homepage, name='homepage'),
    
    # Chat API endpoints
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/chat/clear/', views.clear_chat, name='clear_chat'),
]