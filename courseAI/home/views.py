from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import os
from cerebras.cloud.sdk import Cerebras

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

@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    """Handle chatbot conversations using Cerebras API"""
    try:
        # Parse the JSON request
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Initialize Cerebras client
        client = Cerebras(
            api_key=os.environ.get("CEREBRAS_API_KEY")
        )
        
        # Get conversation history from session
        if 'chat_history' not in request.session:
            request.session['chat_history'] = []
        
        chat_history = request.session['chat_history']
        
        # Build messages array with system prompt and conversation history
        messages = [
            {
                "role": "system",
                "content": """You are CourseAI Assistant, a helpful AI tutor for an online learning platform. 
                You help students with:
                - Course recommendations and learning paths
                - Explaining complex concepts in simple terms
                - Study tips and strategies
                - Programming help and code examples
                - Career guidance in tech fields
                - General academic support
                
                Keep responses friendly, encouraging, and educational. Use emojis sparingly but appropriately.
                If you don't know something specific about the CourseAI platform, be honest but still try to provide helpful general guidance."""
            }
        ]
        
        # Add conversation history (limit to last 10 exchanges to manage token usage)
        for msg in chat_history[-20:]:  # Last 20 messages (10 exchanges)
            messages.append(msg)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Call Cerebras API
        completion_response = client.chat.completions.create(
            messages=messages,
            model="qwen-3-235b-a22b-instruct-2507",
            stream=False,
            max_completion_tokens=1000,
            temperature=0.7,
            top_p=0.8
        )
        
        # Extract the AI response
        ai_response = completion_response.choices[0].message.content
        
        # Update session with new messages
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": ai_response})
        request.session['chat_history'] = chat_history
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'response': ai_response
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        # Log the error in production
        print(f"Chat API Error: {str(e)}")
        return JsonResponse({
            'error': 'Sorry, I encountered an issue. Please try again.',
            'details': str(e) if os.environ.get('DEBUG') else None
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def clear_chat(request):
    """Clear the chat history from session"""
    try:
        if 'chat_history' in request.session:
            del request.session['chat_history']
            request.session.modified = True
        
        return JsonResponse({'success': True, 'message': 'Chat history cleared'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
