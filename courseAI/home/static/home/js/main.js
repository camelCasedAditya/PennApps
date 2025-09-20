// CourseAI Homepage JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('CourseAI Homepage loaded');
    initializeChatbot();
});

// Chatbot functionality
function initializeChatbot() {
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');
    
    if (chatInput) {
        chatInput.focus();
    }
    
    // Scroll to bottom of messages
    scrollToBottom();
}

function openChatbot() {
    // Smooth scroll to chatbot section
    document.getElementById('chatbot').scrollIntoView({ 
        behavior: 'smooth' 
    });
    
    // Focus on input after scroll
    setTimeout(() => {
        document.getElementById('chatInput').focus();
    }, 1000);
}

function handleEnterKey(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();
    
    if (message === '') return;
    
    // Add user message to chat
    addMessage(message, 'user');
    
    // Clear input
    chatInput.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    // Simulate AI response (replace with actual API call)
    setTimeout(() => {
        hideTypingIndicator();
        const response = generateMockResponse(message);
        addMessage(response, 'bot');
    }, 1500);
}

function addMessage(message, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container mb-3 fade-in';
    
    const timestamp = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    if (sender === 'user') {
        messageContainer.innerHTML = `
            <div class="message user-message">
                <div class="message-content">
                    <div class="message-bubble bg-primary text-white p-3 rounded-3">
                        <p class="mb-0">${escapeHtml(message)}</p>
                    </div>
                    <small class="text-muted me-2">${timestamp}</small>
                </div>
                <div class="avatar-sm bg-secondary text-white ms-2">
                    <i class="fas fa-user"></i>
                </div>
            </div>
        `;
    } else {
        messageContainer.innerHTML = `
            <div class="message bot-message">
                <div class="avatar-sm bg-primary text-white me-2">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="message-bubble bg-light p-3 rounded-3">
                        <p class="mb-0">${message}</p>
                    </div>
                    <small class="text-muted ms-2">${timestamp}</small>
                </div>
            </div>
        `;
    }
    
    chatMessages.appendChild(messageContainer);
    scrollToBottom();
}

function showTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const typingContainer = document.createElement('div');
    typingContainer.className = 'message-container mb-3 typing-indicator';
    typingContainer.id = 'typingIndicator';
    
    typingContainer.innerHTML = `
        <div class="message bot-message">
            <div class="avatar-sm bg-primary text-white me-2">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble bg-light p-3 rounded-3">
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(typingContainer);
    typingContainer.classList.add('show');
    scrollToBottom();
}

function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function clearChat() {
    const chatMessages = document.getElementById('chatMessages');
    
    // Keep only the welcome message
    const welcomeMessage = chatMessages.firstElementChild;
    chatMessages.innerHTML = '';
    chatMessages.appendChild(welcomeMessage);
    
    // Reset input
    document.getElementById('chatInput').value = '';
    document.getElementById('chatInput').focus();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Mock AI responses (replace with actual API integration)
function generateMockResponse(userMessage) {
    const message = userMessage.toLowerCase();
    
    // Simple keyword-based responses
    if (message.includes('course') || message.includes('recommend')) {
        return `🎓 Great question! Based on our current offerings, I'd recommend checking out our programming fundamentals, data science, or web development tracks. Each course is designed with interactive lessons and hands-on projects.
        <br><br>
        <strong>💡 Tip:</strong> You can browse all available courses by clicking the "Browse Courses" button above!`;
    }
    
    if (message.includes('machine learning') || message.includes('ai') || message.includes('artificial intelligence')) {
        return `🤖 Machine Learning is a fascinating field! It's a subset of AI that enables computers to learn and make decisions from data without being explicitly programmed.
        <br><br>
        <strong>Key concepts include:</strong>
        <ul>
            <li>Supervised Learning (with labeled data)</li>
            <li>Unsupervised Learning (finding patterns)</li>
            <li>Neural Networks and Deep Learning</li>
            <li>Data preprocessing and feature engineering</li>
        </ul>
        <br>
        Would you like me to recommend some beginner-friendly ML courses?`;
    }
    
    if (message.includes('help') || message.includes('how') || message.includes('what')) {
        return `📚 I'm here to help! I can assist you with:
        <br><br>
        <ul>
            <li><strong>Course Recommendations:</strong> Find the perfect learning path</li>
            <li><strong>Concept Explanations:</strong> Break down complex topics</li>
            <li><strong>Study Tips:</strong> Effective learning strategies</li>
            <li><strong>Technical Questions:</strong> Programming, math, science topics</li>
            <li><strong>Career Guidance:</strong> Skills for different career paths</li>
        </ul>
        <br>
        What specific topic would you like to explore today?`;
    }
    
    if (message.includes('python') || message.includes('programming')) {
        return `🐍 Python is an excellent choice for beginners! It's versatile, readable, and used in web development, data science, AI, automation, and more.
        <br><br>
        <strong>Getting started with Python:</strong>
        <ul>
            <li>Variables and data types</li>
            <li>Control structures (if/else, loops)</li>
            <li>Functions and modules</li>
            <li>Object-oriented programming</li>
            <li>Popular libraries (NumPy, Pandas, Django)</li>
        </ul>
        <br>
        Would you like some practice exercises or course recommendations?`;
    }
    
    if (message.includes('hello') || message.includes('hi') || message.includes('hey')) {
        return `👋 Hello! Welcome to CourseAI! I'm excited to help you on your learning journey. 
        <br><br>
        Whether you're looking to start a new skill, advance your career, or explore a hobby, I'm here to guide you. What would you like to learn about today?`;
    }
    
    if (message.includes('thank') || message.includes('thanks')) {
        return `😊 You're very welcome! I'm glad I could help. Remember, learning is a journey, and every question brings you closer to your goals. 
        <br><br>
        Feel free to ask me anything else - I'm here 24/7 to support your learning adventure!`;
    }
    
    // Default response
    return `🤔 That's an interesting question! While I'm still learning (this is a demo interface), I'd love to help you explore that topic further.
    <br><br>
    <strong>In the full version, I'll be able to:</strong>
    <ul>
        <li>Provide detailed explanations on any subject</li>
        <li>Create personalized study plans</li>
        <li>Answer technical questions with code examples</li>
        <li>Recommend resources and practice exercises</li>
    </ul>
    <br>
    For now, try asking about courses, programming, or study tips! 📚✨`;
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add some interactive features to cards
document.querySelectorAll('.card').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-5px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});