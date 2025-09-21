# CourseAI Chatbot Setup Guide

## Overview
Your Django application now has a fully functional AI chatbot powered by Cerebras! The chatbot maintains conversation history and provides continuous, context-aware responses.

## Environment Setup

### 1. Set your Cerebras API Key
You need to set your Cerebras API key as an environment variable:

**Windows (PowerShell):**
```powershell
$env:CEREBRAS_API_KEY="your_api_key_here"
```

**Windows (Command Prompt):**
```cmd
set CEREBRAS_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export CEREBRAS_API_KEY="your_api_key_here"
```

### 2. For Production
Add the API key to your production environment or create a `.env` file:
```
CEREBRAS_API_KEY=your_api_key_here
```

## Features Implemented

### 🤖 AI Chat Backend
- **File:** `home/views.py`
- Real-time AI responses using Cerebras API
- Error handling and fallback responses
- Conversation memory management

### 🌐 API Endpoints
- **File:** `home/urls.py`
- `POST /api/chat/` - Send messages to AI
- `POST /api/chat/clear/` - Clear conversation history

### 💬 Frontend Integration
- **File:** `home/static/home/js/main.js`
- Real API calls instead of mock responses
- Proper error handling and user feedback
- Conversation context preservation

### 📱 Session Management
- Conversation history stored in Django sessions
- Continuous chat experience across page reloads
- Automatic context management (last 20 messages)

## How to Test

### 1. Start your Django server
```bash
cd courseAI
python manage.py runserver
```

### 2. Visit your homepage
Navigate to `http://localhost:8000` and scroll to the chatbot section.

### 3. Test the chatbot
Try these sample questions:
- "What programming language should I learn first?"
- "Explain machine learning in simple terms"
- "Give me some study tips for coding"
- "What career paths are available in tech?"

### 4. Test conversation memory
Ask follow-up questions to verify the AI remembers previous context:
- First: "Tell me about Python"
- Then: "What are some good projects to practice it?"

## Troubleshooting

### Common Issues

1. **API Key Error**
   - Ensure `CEREBRAS_API_KEY` environment variable is set
   - Check that the API key is valid and active

2. **No Response from Chatbot**
   - Check browser console for JavaScript errors
   - Verify Django server is running
   - Check Django logs for Python errors

3. **CSRF Token Issues**
   - The chat endpoints use `@csrf_exempt` decorator
   - If issues persist, add CSRF token to fetch requests

### Debug Mode
Set `DEBUG=True` in Django settings to see detailed error messages in API responses.

## Customization

### Modify AI Personality
Edit the system prompt in `home/views.py` around line 35:
```python
{
    "role": "system",
    "content": """Your custom system prompt here..."""
}
```

### Adjust Response Length
Modify `max_completion_tokens` in the API call (currently set to 1000).

### Change Conversation Memory
Adjust the history limit in `home/views.py` around line 45:
```python
for msg in chat_history[-20:]:  # Change 20 to desired limit
```

## Security Notes

- API key should never be committed to version control
- Consider rate limiting for production use
- Add proper authentication if needed
- Monitor API usage costs

## Next Steps

Consider adding:
- User authentication for personalized conversations
- Rate limiting to prevent abuse
- Conversation export/import functionality
- Multi-language support
- Voice input/output capabilities

Your chatbot is now ready to provide intelligent, continuous assistance to your CourseAI users! 🚀