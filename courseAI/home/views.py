from django.shortcuts import render
from django.views.generic import TemplateView

# Create your views here.

class HomePageView(TemplateView):
    """Main homepage view with chatbot interface"""
    template_name = 'home/homepage.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'CourseAI - AI-Powered Learning'
        return context

def homepage(request):
    """Function-based view for homepage"""
    return render(request, 'home/homepage.html', {
        'page_title': 'CourseAI - AI-Powered Learning'
    })
