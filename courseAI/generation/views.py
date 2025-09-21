from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime
from cerebras.cloud.sdk import Cerebras
from pinecone import Pinecone
from tavily import TavilyClient
import dotenv  
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
from .models import CourseGeneration, GeneratedChapter, GeneratedLesson, LessonType, GenerationLog, MultipleChoiceQuiz, QuizAttempt, QuizAttempt, ArticleContent, YouTubeVideo, ExternalArticles, TextResponseQuestion, TextResponseSubmission
from django.db import transaction
from django.utils import timezone
from .youtube_utils import generate_youtube_query, search_youtube
from courses.models import Project, File

# --------------- Sidebar helpers ---------------
def _sidebar_context_for_lesson(lesson: GeneratedLesson):
    """Build common context for sidebar navigation given a current lesson."""
    course = lesson.chapter.course_generation
    chapters = (GeneratedChapter.objects
                .filter(course_generation=course)
                .prefetch_related('lessons', 'lessons__quiz', 'lessons__article', 'lessons__external_article'))
    return {
        'course_generation': course,
        'sidebar_chapters': chapters,
        'current_lesson_id': lesson.id,
    }

dotenv.load_dotenv()  # Load environment variables from .env file
client = Cerebras(
    api_key=os.getenv('CEREBRAS_API_KEY'),
    max_retries=5
)

second_client = Cerebras(
    api_key=os.getenv('SECOND_CEREBRAS_API_KEY'),
    max_retries=5
)


def generation_form(request):
    """Display the course generation form."""
    # Get recent course generations to display
    recent_courses = CourseGeneration.objects.filter(
        status='completed'
    ).order_by('-completed_at')[:5]
    
    context = {
        'recent_courses': recent_courses
    }
    return render(request, 'generation/form.html', context)


def chapter_list_create(input_prompt, exp):
    """Generate chapter list using Cerebras API with fallback to secondary client."""
    messages = [
        {
            "role": "system",
            "content": f"""
                You are an expert learning strategist and educational content designer. Your task is to help a user break down a massive project into a structured learning plan.

                Input: 
                - The user will provide a single sentence describing a large, complex project they want to complete.
                - This is the experience the following user has with the project: {exp}

                Task: 
                1. Analyze the project and determine all the key areas, topics, or skills that the user will need to learn in order to successfully complete the project.
                2. Break these areas down into sequential "chapters" or learning modules.
                3. For each chapter, provide:
                - A chapter number (starting from 1)
                - A descriptive chapter name
                - A brief description explaining what the chapter covers
                - A difficulty rating from 1 to 10, indicating how challenging this chapter is to learn

                Output: Provide the results as a JSON array with the following structure:

                [
                {{
                    "chapter_number": "",
                    "chapter_name": "",
                    "chapter_description": "",
                    "chapter_difficulty": ""
                }},
                ...
                ]

                Make sure the chapters are logically ordered so that mastering one chapter naturally prepares the learner for the next. Focus on completeness and clarity, 
                covering all areas necessary to achieve the project goal. Use concise, clear language for the descriptions. Make sure that the chapters are very extensive. It is better to have too much than too little.
                The maximum number of chapters is 5.
                
                Do not include any additional commentary or explanation outside of the JSON array.
                """,
        },
        {
            "role": "user",
            "content": input_prompt,
        }
    ]
    
    # Try primary client first
    try:
        print("🔄 Attempting chapter generation with primary Cerebras client...")
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="qwen-3-coder-480b",
        )
        response_content = chat_completion.choices[0].message.content
        print("✅ Primary client succeeded for chapter generation")
    except Exception as e:
        print(f"❌ Primary client failed for chapter generation: {str(e)}")
        try:
            print("🔄 Retrying with secondary Cerebras client...")
            chat_completion = second_client.chat.completions.create(
                messages=messages,
                model="qwen-3-coder-480b",
            )
            response_content = chat_completion.choices[0].message.content
            print("✅ Secondary client succeeded for chapter generation")
        except Exception as e2:
            print(f"❌ Secondary client also failed for chapter generation: {str(e2)}")
            raise Exception(f"Both Cerebras clients failed for chapter generation. Primary: {str(e)}, Secondary: {str(e2)}")

    response_content = chat_completion.choices[0].message.content
    try:
        chapter_list = json.loads(response_content.strip())
    except json.JSONDecodeError as e:
        print(f"JSON decode error in chapter_list_create: {e}")
        print(f"Response content length: {len(response_content)}")
        # Try to extract JSON between first [ and last ]
        start = response_content.find('[')
        end = response_content.rfind(']')
        if start != -1 and end > start:
            json_str = response_content[start:end+1].strip()
            try:
                chapter_list = json.loads(json_str)
            except json.JSONDecodeError as e2:
                print(f"Failed to parse extracted JSON: {e2}")
                raise ValueError("Unable to parse chapter list JSON")
        else:
            raise ValueError("No JSON array found in response")
    
    return chapter_list

def create_lesson(chapter_item, course_structure, prompt):
    """Create a lesson plan for a single chapter."""
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"""
                     You are an expert curriculum and instructional designer. 
                        Your task is to create a detailed lesson plan for ONE chapter at a time, 
                        based on the project and chapter structure provided.

                        Context:
                        - This the the current project the user wants to learn the following project: {prompt}
                        - This is the overall learning structure for the entire project: {course_structure}

                        Task:  
                            1. Analyze the chapter details in {chapter_item} and use the difficulty rating to decide how many lessons to generate:  
                            - Minimum: 5 lessons  
                            - Maximum: 8 lessons  
                            - Higher difficulty = more lessons.  

                            2. Randomize lesson structure: Do not use the same number or type of lessons across different chapters. Each chapter's lessons should feel unique and adapted to the chapter's content.  

                            3. For each lesson, fill in the following fields:  
                            - "lesson_number": sequential lesson number (starting at 1)  
                            - "lesson_type": pick one option from the lesson options list below  
                            - "lesson_type_ID": based off of the lesson type, find the corresponding lesson type ID from the lesson options list below
                            - "lesson_name": a concise but engaging title  
                            - "lesson_description": short summary of what the lesson covers  
                            - "lesson_details": detailed explanation of what will be taught and how it connects to the chapter  
                            - "lesson_goals": clear learning objectives (bullet style or short list)  
                            - "lesson_guidlines": a step by step guide on how to create the lesson in way which will make sense, cohesive, and useful. This is for other teachers who will be creating the actual lessons.

                            4. Ensure coherence: The lessons should logically connect, flow naturally, and cover everything needed for the learner to master this chapter. Make sure to include different types, they are all valuable in different ways. 

                            5. Lesson come in 2 forms: learning lessons and practice lessons. Learning lessons are not hands on and used to introduce a new topic that the student hasn't learnt yet. 
                            Practice lessons are designed to reinforce and apply what has been learned through learning lessons, they are usually more hands on. Make sure to include a mix of both types of lessons in the plan and don't do a practice lesson before introducing the topic in learning lesson first.

                          6. Output Format: Return ONLY valid JSON in the following structure (no explanations, no extra text):  
                            
                            Output Structure:
                                "lesson_number": "",
                                "lesson_type": "",
                                "lesson_type_ID": "",
                                "lesson_name": "",
                                "lesson_description": "",
                                "lesson_details": "",
                                "lesson_goals": "",
                                "lesson_guidlines": ""
                        
                        Lesson options: 

                        Learning Lessons:
                        Video - Name: vid, ID: 1,
                        AI generated articles- Name: art , ID: 2,
                        External Article Reading- Name: ext , ID: 3,

                        Practice Lessons:
                        Interactive programming exercise - Name: int , ID: 5,
                        Multiple choice quiz - Name: mcq , ID: 6,
                        text response - Name: txt , ID: 7,

                        7. DO NOT RETURN ANYTHING OTHER THAN THE JSON. NO EXPLANATIONS, NO EXTRA TEXT. ONLY THE RAW JSON.
                        """,
            }
        ],
        model="qwen-3-coder-480b",
    )

    # Video - Name: vid, ID: 1,
    #                     Text response - Name: txt , ID: 2,
    #                     Multiple choice quiz - Name: mcq , ID: 3,
    #                     Interactive exercise - Name: int , ID: 4,
    #                     Article or reading - Name: art , ID: 5,
    #                     conclusion and summary - Name: sum, ID: 6,
    #                     external resource review - Name: ext, ID: 7
    #                     code - Name: code, ID: 8

    try:
        lesson_plan = json.loads(chat_completion.choices[0].message.content.strip())
    except json.JSONDecodeError as e:
        print(f"JSON decode error in create_lesson: {e}")
        print(f"Response content length: {len(chat_completion.choices[0].message.content)}")
        # Try to extract JSON between first [ and last ]
        response_content = chat_completion.choices[0].message.content
        start = response_content.find('[')
        end = response_content.rfind(']')
        if start != -1 and end > start:
            json_str = response_content[start:end+1].strip()
            try:
                lesson_plan = json.loads(json_str)
            except json.JSONDecodeError as e2:
                print(f"Failed to parse extracted JSON: {e2}")
                raise ValueError("Unable to parse lesson plan JSON")
        else:
            raise ValueError("No JSON array found in response")
    return lesson_plan

def ensure_lesson_types_exist():
    """Ensure all lesson types exist in the database."""
    lesson_types = [
        ('vid', 1, 'Video'),
        ('txt', 2, 'Text Response'),
        ('mcq', 3, 'Multiple Choice Quiz'),
        ('int', 4, 'Interactive Exercise'),
        ('art', 5, 'Article or Reading'),
        ('sum', 6, 'Conclusion and Summary'),
        ('ext', 7, 'External Resource Review'),
        ('code', 8, 'Code'),
    ]
    
    for name, type_id, display_name in lesson_types:
        LessonType.objects.get_or_create(
            name=name,
            defaults={
                'type_id': type_id,
                'display_name': display_name,
                'description': f'{display_name} lesson type'
            }
        )


pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

index = pc.Index(host=os.getenv('PINECONE_HOST'))

def get_best_source(question, min_score=0.5):
    print(f"🔍 get_best_source called with question: {question[:100]}...")
    try:
        # Initialize Tavily client
        tavily_api_key = os.getenv('TAVILY_API_KEY')
        print(f"🔍 Tavily API key found: {bool(tavily_api_key)}")
        if not tavily_api_key:
            print("❌ No TAVILY_API_KEY found in environment variables!")
            return None
            
        tavily_client = TavilyClient(api_key=tavily_api_key)

        completion_create_response12 = client.chat.completions.create(
            messages=[
                    {
                        "role": "user",
                        "content": f"""
                            Please take the following information and simplify it down to a simple question containing the main ideas. 
                            Input: {question}
                            DO NOT return anything other than the main ideas, do not explain anything, do not add any extra information.
                        """
                    }
                ],
                model="qwen-3-235b-a22b-instruct-2507",
                stream=False,
                max_completion_tokens=20000,
                temperature=0.7,
                top_p=0.8
            )
        print(completion_create_response12)
    
    # Extract the text content from the response
        main_ideas = completion_create_response12.choices[0].message.content

        # Perform search
        print(f"🔍 Performing Tavily search...")
        response = tavily_client.search(main_ideas)
        print(f"🔍 Tavily search response received: {len(response.get('results', []))} results")
        
        # Find the best result above the score threshold
        results = response.get('results', [])
        best_result = None
        best_score = 0
        
        for i, result in enumerate(results):
            score = result.get('score', 0)
            url = result.get('url', '')
            print(f"🔍 Result {i+1}: score={score}, url={url[:50]}...")
            
            if score >= min_score and url and score > best_score:
                best_result = {
                    'url': url,
                    'title': result.get('title', 'No title available'),
                    'content': result.get('content', 'No content available'),
                    'score': score
                }
                best_score = score
                print(f"🔍 New best result found with score {score}")
        
        print(f"🔍 Final best result: {best_result}")
        return best_result
        
    except Exception as e:
        print(f"❌ Error during search: {e}")
        import traceback
        traceback.print_exc()
        return None

def ai_gen_article(input):

    articontext = f"""Description: {input.lesson_description}
        Details: {input.lesson_details}
        Goals: {input.lesson_goals}
        Guidelines: {input.lesson_guidelines}
        """

    completion_create_response1 = client.chat.completions.create(
    messages=[
            {
                "role": "user",
                "content": f"""
                    Please take the following information and simplify it down to a few main ideas. They should be a few words at most.
                    Input: {articontext}
                    DO NOT return anything other than the main ideas, do not explain anything, do not add any extra information.
                """
            }
        ],
        model="qwen-3-235b-a22b-instruct-2507",
        stream=False,
        max_completion_tokens=20000,
        temperature=0.7,
        top_p=0.8
    )

    print(completion_create_response1)
    
    # Extract the text content from the response
    main_ideas = completion_create_response1.choices[0].message.content

    filtered_results = index.search(
        namespace="pennapps", 
        query={
            "inputs": {"text": main_ideas}, 
            "top_k": 3,
        },
        fields=["category", "chunk_text"]
    )
    print(filtered_results)


    completion_create_response = client.chat.completions.create(
    messages=[
            {
                "role": "system",
                "content": f"""You are a renowned article writer celebrated for producing high-quality, detailed, and comprehensive articles on a wide range of topics. Your strengths include breaking down complex concepts into clear, engaging explanations, providing accurate and up-to-date information, and adjusting your tone from formal to conversational as needed. You cite sources when relevant and always ensure clarity and depth.

                    You have been given the following input from a wealthy client who wants to learn as much as possible about the subject, within the boundaries of the provided material:

                    Input: {articontext}
                    Additional Information: {filtered_results}

                    Write the best possible article based on this material. The article should be long enough to cover the topic thoroughly, but not so lengthy that it becomes overwhelming. Present only the article itself—no extra commentary outside of the article.
                    Please return it in markdown format. DO NOT INCLUDE ANYTHING OTHER THAN THE ARTICLE.
                """
            }
        ],
        model="qwen-3-235b-a22b-instruct-2507",
        stream=False,
        max_completion_tokens=20000,
        temperature=0.7,
        top_p=0.8
    )

    # Extract and return the article content as a string
    article = completion_create_response.choices[0].message.content
    return article

def generate_quiz(lesson):
    """Generate a multiple choice quiz for a given lesson using Cerebras API."""
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """
                    You are an expert educational content creator specializing in assessment design.
                    Your task is to create a multiple-choice quiz based on the provided lesson content.

                    Generate 5-10 multiple-choice questions that test the key concepts from the lesson.
                    Each question should have:
                    - A clear, concise question
                    - 4 answer options (A, B, C, D)
                    - The correct answer indicated
                    - A brief explanation for the correct answer

                    Output format: Return ONLY valid JSON in the following structure:
                    {
                        "questions": [
                            {
                                "question": "What is the capital of France?",
                                "options": {
                                    "A": "London",
                                    "B": "Paris",
                                    "C": "Berlin",
                                    "D": "Madrid"
                                },
                                "correct_answer": "B",
                                "explanation": "Paris is the capital and most populous city of France."
                            },
                            ...
                        ]
                    }

                    Make questions progressively more challenging and ensure they cover different aspects of the lesson content.
                    DO NOT include any additional text outside the JSON.
                """,
            },
            {
                "role": "user",
                "content": f"""
                    Lesson Name: {lesson.lesson_name}
                    Lesson Description: {lesson.lesson_description}
                    Lesson Details: {lesson.lesson_details}
                    Lesson Goals: {lesson.lesson_goals}
                """,
            }
        ],
        model="qwen-3-coder-480b",
    )

    response_content = chat_completion.choices[0].message.content
    try:
        quiz_data = json.loads(response_content.strip())
    except json.JSONDecodeError as e:
        print(f"JSON decode error in generate_quiz: {e}")
        print(f"Response content length: {len(response_content)}")
        # Try to extract JSON between first { and last }
        start = response_content.find('{')
        end = response_content.rfind('}')
        if start != -1 and end > start:
            json_str = response_content[start:end+1].strip()
            try:
                quiz_data = json.loads(json_str)
            except json.JSONDecodeError as e2:
                print(f"Failed to parse extracted JSON: {e2}")
                raise ValueError("Unable to parse quiz JSON")
        else:
            raise ValueError("No JSON object found in response")
    
    # Create the MultipleChoiceQuiz object
    quiz = MultipleChoiceQuiz.objects.create(
        lesson=lesson,
        quiz_data=quiz_data
    )
    
    return quiz

def process_single_chapter(chapter, chapter_item, course_structure_text, user_text, course_generation):
    """Process a single chapter in parallel - generate lessons and content."""
    chapter_lessons_count = 0
    chapter_result = {
        'chapter_number': chapter.chapter_number,
        'lesson_plan': None,
        'lessons_count': 0,
        'error': None
    }
    
    try:
        print(f"🔄 Generating lessons for Chapter {chapter.chapter_number}...")
        
        GenerationLog.objects.create(
            course_generation=course_generation,
            step=f"lesson_generation_chapter_{chapter.chapter_number}",
            status="in_progress",
            message=f"Generating lessons for Chapter {chapter.chapter_number}"
        )
        
        # Generate lesson plan
        lesson_plan = create_lesson(chapter_item, course_structure_text, user_text)
        chapter_result['lesson_plan'] = lesson_plan
        
        # Save lessons to database
        with transaction.atomic():
            for lesson_data in lesson_plan:
                GeneratedLesson.objects.create(
                    chapter=chapter,
                    lesson_number=int(lesson_data.get("lesson_number", 1)),
                    lesson_type=lesson_data.get("lesson_type", ""),
                    lesson_type_id=lesson_data.get("lesson_type_ID"),
                    lesson_name=lesson_data.get("lesson_name", ""),
                    lesson_description=lesson_data.get("lesson_description", ""),
                    lesson_details=lesson_data.get("lesson_details", ""),
                    lesson_goals=lesson_data.get("lesson_goals", ""),
                    lesson_guidelines=lesson_data.get("lesson_guidlines", "")
                )
                chapter_lessons_count += 1
            
            GenerationLog.objects.create(
                course_generation=course_generation,
                step=f"lesson_generation_chapter_{chapter.chapter_number}",
                status="completed",
                message=f"Generated {len(lesson_plan)} lessons for Chapter {chapter.chapter_number}"
            )
        
        # Process each lesson type
        lessons = GeneratedLesson.objects.filter(chapter=chapter)
        for lesson in lessons:
            print(f"🔍 Processing lesson {lesson.lesson_number} with type: '{lesson.lesson_type}' in Chapter {chapter.chapter_number}")
            try:
                if lesson.lesson_type == 'mcq':
                    quiz = generate_quiz(lesson)
                    print(f"✅ Generated quiz for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}, Quiz ID: {quiz.id}")
                elif lesson.lesson_type == "int":
                    generate_programming_exercise(lesson)
                    print(f"✅ Generated programming exercise for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}")
                elif lesson.lesson_type == "vid":
                    search_youtube_for_lesson(lesson)  
                    print(f"✅ Prepared YouTube search for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}")
                elif lesson.lesson_type == "txt":
                    generate_text_response_questions(lesson)
                    print(f"✅ Generated text response questions for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}")
                elif lesson.lesson_type == "ext":
                    print(f"🔍 Found EXT lesson type! Processing external article for lesson {lesson.lesson_number}")
                    source = get_best_source(f"{lesson.lesson_name}. {lesson.lesson_description} {lesson.lesson_details}")
                    if source and source.get('url'):
                        ExternalArticles.objects.create(
                            lesson=lesson,
                            url=source['url']
                        )
                        print(f"✅ Saved external article URL for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}: {source['url']}")
                    else:
                        print(f"⚠️ No suitable external article found for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}")
                elif lesson.lesson_type == "art":
                    article = ai_gen_article(lesson)
                    ArticleContent.objects.create(
                        lesson=lesson,
                        content=article
                    )
                    print(f"✅ Generated article for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}")
            except Exception as lesson_error:
                print(f"❌ Error processing lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}: {str(lesson_error)}")
                # Continue processing other lessons even if one fails
        
        chapter_result['lessons_count'] = chapter_lessons_count
        print(f"✅ Completed processing Chapter {chapter.chapter_number} with {chapter_lessons_count} lessons")
        
    except Exception as e:
        print(f"❌ Error processing Chapter {chapter.chapter_number}: {str(e)}")
        traceback.print_exc()
        chapter_result['error'] = str(e)
        
        # Log the error
        try:
            GenerationLog.objects.create(
                course_generation=course_generation,
                step=f"lesson_generation_chapter_{chapter.chapter_number}",
                status="failed",
                level="error",
                message=f"Failed to generate lessons for Chapter {chapter.chapter_number}: {str(e)}"
            )
        except Exception as log_error:
            print(f"❌ Failed to log error for Chapter {chapter.chapter_number}: {str(log_error)}")
    
    return chapter_result

def create_final_project_chapter(course_generation, user_prompt, chapter_number):
    """Create a final project chapter with one interactive programming exercise lesson."""
    try:
        print(f"🔄 Creating final project chapter {chapter_number}...")
        
        # Create the final project chapter
        final_chapter = GeneratedChapter.objects.create(
            course_generation=course_generation,
            chapter_number=chapter_number,
            chapter_name="Final Project",
            chapter_description=f"Comprehensive project that applies all concepts learned throughout the course to build: {user_prompt}",
            difficulty_rating=10  # Maximum difficulty as it's the final project
        )
        
        GenerationLog.objects.create(
            course_generation=course_generation,
            step=f"final_project_chapter_{chapter_number}",
            status="in_progress",
            message=f"Creating final project chapter {chapter_number}"
        )
        
        # Generate a comprehensive programming exercise using AI
        lesson_content = generate_final_project_lesson_content(user_prompt)
        
        # Create the interactive programming exercise lesson
        final_lesson = GeneratedLesson.objects.create(
            chapter=final_chapter,
            lesson_number=1,
            lesson_type="int",  # Interactive programming exercise
            lesson_type_id=5,
            lesson_name=f"Build Your Own: {user_prompt.split()[0:5]}...",  # First 5 words + ellipsis
            lesson_description=f"Create a complete implementation of: {user_prompt}",
            lesson_details=lesson_content['details'],
            lesson_goals=lesson_content['goals'],
            lesson_guidelines=lesson_content['guidelines']
        )
        
        # Generate the programming exercise for this lesson
        project = generate_comprehensive_final_project(final_lesson, user_prompt)
        
        GenerationLog.objects.create(
            course_generation=course_generation,
            step=f"final_project_chapter_{chapter_number}",
            status="completed",
            message=f"Created final project chapter {chapter_number} with comprehensive programming exercise"
        )
        
        # Create lesson plan format for consistency
        lesson_plan = [{
            "lesson_number": 1,
            "lesson_type": "int",
            "lesson_type_ID": 5,
            "lesson_name": final_lesson.lesson_name,
            "lesson_description": final_lesson.lesson_description,
            "lesson_details": final_lesson.lesson_details,
            "lesson_goals": final_lesson.lesson_goals,
            "lesson_guidlines": final_lesson.lesson_guidelines
        }]
        
        print(f"✅ Successfully created final project chapter {chapter_number}")
        
        return {
            'success': True,
            'chapter_number': chapter_number,
            'lesson_plan': lesson_plan,
            'lessons_count': 1,
            'error': None
        }
        
    except Exception as e:
        print(f"❌ Error creating final project chapter: {str(e)}")
        traceback.print_exc()
        
        try:
            GenerationLog.objects.create(
                course_generation=course_generation,
                step=f"final_project_chapter_{chapter_number}",
                status="failed",
                level="error",
                message=f"Failed to create final project chapter: {str(e)}"
            )
        except Exception as log_error:
            print(f"❌ Failed to log error for final project chapter: {str(log_error)}")
        
        return {
            'success': False,
            'chapter_number': chapter_number,
            'lesson_plan': None,
            'lessons_count': 0,
            'error': str(e)
        }

def generate_final_project_lesson_content(user_prompt):
    """Generate detailed lesson content for the final project using AI."""
    messages = [
        {
            "role": "system",
            "content": """
                You are an expert curriculum designer creating a comprehensive final project lesson.
                Your task is to create detailed lesson content for a capstone programming project that synthesizes 
                all the concepts a student has learned throughout their course.

                The final project should be:
                - Comprehensive and challenging
                - Practical and applicable to real-world scenarios
                - Allow students to showcase their complete understanding
                - Include multiple components and features
                - Be ambitious but achievable

                Return your response as JSON with the following structure:
                {
                    "details": "Comprehensive explanation of what the final project entails, including all major components, features, and technical requirements. This should be detailed enough for a student to understand the full scope.",
                    "goals": "Clear learning objectives and outcomes. What skills and knowledge will students demonstrate? What will they have accomplished upon completion?",
                    "guidelines": "Step-by-step breakdown of how to approach this project. Include phases, milestones, and key considerations for successful completion."
                }

                Make this substantial - this is the culmination of their entire learning journey.
                DO NOT include any additional text outside the JSON.
                """,
        },
        {
            "role": "user",
            "content": f"""
                Create a comprehensive final project lesson for a student who wants to learn how to: {user_prompt}
                
                This should be the capstone project that brings together everything they've learned throughout the course.
                Make it challenging, practical, and comprehensive.
                """,
        }
    ]
    
    # Try primary client first
    try:
        print("🔄 Generating final project lesson content with primary Cerebras client...")
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="qwen-3-coder-480b",
        )
        print("✅ Primary client succeeded for final project lesson content")
    except Exception as e:
        print(f"❌ Primary client failed for final project lesson content: {str(e)}")
        try:
            print("🔄 Retrying final project lesson content with secondary Cerebras client...")
            chat_completion = second_client.chat.completions.create(
                messages=messages,
                model="qwen-3-coder-480b",
            )
            print("✅ Secondary client succeeded for final project lesson content")
        except Exception as e2:
            print(f"❌ Secondary client also failed for final project lesson content: {str(e2)}")
            # Provide fallback content
            return {
                'details': f"Create a comprehensive implementation of: {user_prompt}. This final project should demonstrate mastery of all concepts learned throughout the course, including proper code structure, error handling, user interface design, and real-world applicability.",
                'goals': "Demonstrate complete understanding and application of all course concepts; Create a fully functional, production-ready implementation; Showcase problem-solving and software design skills",
                'guidelines': "1. Plan your project architecture and design; 2. Implement core functionality step by step; 3. Add advanced features and optimizations; 4. Test thoroughly and handle edge cases; 5. Document your code and create user instructions; 6. Prepare a presentation of your final work"
            }
    
    try:
        response_content = chat_completion.choices[0].message.content.strip()
        lesson_content = json.loads(response_content)
        return lesson_content
    except json.JSONDecodeError as e:
        print(f"JSON decode error in final project lesson content: {e}")
        # Try to extract JSON
        start = response_content.find('{')
        end = response_content.rfind('}')
        if start != -1 and end > start:
            try:
                lesson_content = json.loads(response_content[start:end+1])
                return lesson_content
            except json.JSONDecodeError:
                pass
        
        # Fallback content if JSON parsing fails
        return {
            'details': f"Create a comprehensive implementation of: {user_prompt}. This final project should demonstrate mastery of all concepts learned throughout the course.",
            'goals': "Demonstrate complete understanding and application of all course concepts",
            'guidelines': "Plan, implement, test, and document your complete solution step by step"
        }

def generate_comprehensive_final_project(lesson, user_prompt):
    """Generate a comprehensive programming project for the final lesson."""
    messages = [
        {
            "role": "system",
            "content": """
                You are an expert programming instructor creating a comprehensive final project.
                This should be a substantial, multi-file programming project that serves as the capstone 
                of the student's learning journey.

                Create a comprehensive project that includes:
                - Multiple interconnected files and modules
                - Complex functionality that showcases various programming concepts
                - Proper code structure and organization
                - Advanced features beyond basic implementation
                - Starter code that provides structure but requires significant implementation

                The project should be ambitious and comprehensive - this is their final demonstration of mastery.

                Output format: Return ONLY valid JSON in the following structure:
                {
                    "starter_files": {
                        "main.py": "# Main application entry point\\n# TODO: Implement main functionality",
                    },
                    "grading_method": "ai_review",
                    "expected_output": ""
                }

                Include at least 4-6 files with meaningful starter code and clear TODO instructions.
                Focus on proper software architecture and real-world applicability.
                DO NOT include any additional text outside the JSON.
                """,
        },
        {
            "role": "user",
            "content": f"""
                Create a comprehensive final project for: {user_prompt}
                
                Lesson Details: {lesson.lesson_details}
                Lesson Goals: {lesson.lesson_goals}
                
                This should be the most substantial and comprehensive project in the entire course.
                Include multiple files, advanced features, and demonstrate mastery of all concepts.
                """,
        }
    ]
    
    # Try primary client first
    try:
        print(f"🔄 Generating comprehensive final project with primary Cerebras client...")
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="qwen-3-coder-480b",
        )
        print(f"✅ Primary client succeeded for comprehensive final project")
    except Exception as e:
        print(f"❌ Primary client failed for comprehensive final project: {str(e)}")
        try:
            print(f"🔄 Retrying comprehensive final project with secondary Cerebras client...")
            chat_completion = second_client.chat.completions.create(
                messages=messages,
                model="qwen-3-coder-480b",
            )
            print(f"✅ Secondary client succeeded for comprehensive final project")
        except Exception as e2:
            print(f"❌ Secondary client also failed for comprehensive final project: {str(e2)}")
            # Create fallback project structure
            project_data = {
                "starter_files": {
                    "main.py": f"# Final Project: {user_prompt}\n# TODO: Implement the main functionality\n\ndef main():\n    # Your implementation here\n    pass\n\nif __name__ == '__main__':\n    main()",
                    "README.md": f"# Final Project: {user_prompt}\n\n## Description\nTODO: Describe your project\n\n## Requirements\nTODO: List requirements\n\n## Usage\nTODO: Explain how to use your project"
                },
                "grading_method": "ai_review",
                "expected_output": ""
            }
            
            # Create the Project object with fallback data
            project = Project.objects.create(
                lesson=lesson,
                name=f"Final Project: {user_prompt[:50]}...",
                description=f"Comprehensive final project: {lesson.lesson_description}",
                grading_method=project_data.get('grading_method', 'ai_review'),
                expected_output=project_data.get('expected_output', ''),
                is_final_project=True
            )
            
            # Create File objects for starter files
            starter_files = project_data.get('starter_files', {})
            for filename, content in starter_files.items():
                File.objects.create(
                    project=project,
                    name=filename,
                    relative_path=filename,
                    content=content
                )
            
            print(f"✅ Created fallback comprehensive final project with {len(starter_files)} starter files")
            return project

    try:
        response_content = chat_completion.choices[0].message.content.strip()
        project_data = json.loads(response_content)
    except json.JSONDecodeError as e:
        print(f"JSON decode error in comprehensive final project: {e}")
        # Try to extract JSON between first { and last }
        start = response_content.find('{')
        end = response_content.rfind('}')
        if start != -1 and end > start:
            try:
                project_data = json.loads(response_content[start:end+1])
            except json.JSONDecodeError:
                # Use fallback data
                project_data = {
                    "starter_files": {
                        "main.py": f"# Final Project: {user_prompt}\n# TODO: Implement the main functionality",
                        "README.md": f"# Final Project: {user_prompt}\n\n## Description\nComprehensive final project"
                    },
                    "grading_method": "ai_review",
                    "expected_output": ""
                }
        else:
            # Use fallback data
            project_data = {
                "starter_files": {
                    "main.py": f"# Final Project: {user_prompt}\n# TODO: Implement the main functionality",
                    "README.md": f"# Final Project: {user_prompt}\n\n## Description\nComprehensive final project"
                },
                "grading_method": "ai_review",
                "expected_output": ""
            }
    
    # Create the Project object
    project = Project.objects.create(
        lesson=lesson,
        name=f"Final Project: {user_prompt[:50]}...",
        description=f"Comprehensive final project: {lesson.lesson_description}",
        grading_method=project_data.get('grading_method', 'ai_review'),
        expected_output=project_data.get('expected_output', ''),
        is_final_project=True
    )
    
    # Create File objects for starter files
    starter_files = project_data.get('starter_files', {})
    for filename, content in starter_files.items():
        File.objects.create(
            project=project,
            name=filename,
            relative_path=filename,
            content=content
        )

    print(f"✅ Generated comprehensive final project with {len(starter_files)} starter files")
    return project

@require_http_methods(["POST"])
def process_generation(request):
    """Process the form submission and save all workflow data to database."""
    course_generation = None
    
    try:
        # Ensure lesson types exist
        ensure_lesson_types_exist()
        
        # Get the text from the form
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            user_text = data.get('text', '')
            experience_level = data.get('experience', 'beginner')
        else:
            user_text = request.POST.get('text', '')
            experience_level = request.POST.get('experience', 'beginner')
        
        # Convert experience level to descriptive text
        experience_mapping = {
            'beginner': "I know nothing, I don't even know how to run code or anything.",
            'some_basics': "I have heard of this topic and understand some basic concepts, but I haven't practiced much yet.",
            'intermediate': "I have some experience and knowledge in this area, but I want to learn more advanced concepts.",
            'advanced': "I'm experienced in this area but want to deepen my skills and learn advanced techniques.",
            'expert': "I'm already quite skilled in this area but want to learn cutting-edge techniques and best practices."
        }
        experience_description = experience_mapping.get(experience_level, experience_mapping['beginner'])
        
        # Print the received text to the terminal
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"📝 [{timestamp}] Received text from frontend: {user_text}")
        print(f"📊 Full request data: {json.dumps({'text': user_text, 'experience': experience_level, 'experience_description': experience_description, 'timestamp': timestamp}, indent=2)}")
    
        # Create initial course generation record
        with transaction.atomic():
            course_generation = CourseGeneration.objects.create(
                user_prompt=user_text,
                experience_level=experience_description,
                status='generating'
            )
            
            # Log start
            GenerationLog.objects.create(
                course_generation=course_generation,
                step="generation_started",
                status="started",
                message="Course generation process initiated"
            )
        
        print(f"🚀 [{timestamp}] Starting course generation for ID: {course_generation.id}")
        
        # Generate chapters
        GenerationLog.objects.create(
            course_generation=course_generation,
            step="chapter_generation",
            status="in_progress",
            message="Generating chapter structure"
        )
        
        chapter_list = chapter_list_create(user_text, experience_description)
        
        # Create course structure summary for lesson generation
        course_structure = []
        for item in chapter_list:
            course_structure.append(f"Chapter {item['chapter_number']}: {item['chapter_name']} (Difficulty: {item['chapter_difficulty']}/10)")
        course_structure_text = "\n".join(course_structure)
        
        # Save everything to database
        with transaction.atomic():
            # Update course generation with chapter count
            course_generation.total_chapters = len(chapter_list)
            course_generation.save()
            
            # Save chapters to database
            created_chapters = []
            for chapter_data in chapter_list:
                chapter = GeneratedChapter.objects.create(
                    course_generation=course_generation,
                    chapter_number=int(chapter_data["chapter_number"]),
                    chapter_name=chapter_data["chapter_name"],
                    chapter_description=chapter_data["chapter_description"],
                    difficulty_rating=int(chapter_data["chapter_difficulty"])
                )
                created_chapters.append(chapter)
                print(f"✅ Saved Chapter {chapter.chapter_number}: {chapter.chapter_name}")
            
            GenerationLog.objects.create(
                course_generation=course_generation,
                step="chapter_generation",
                status="completed",
                message=f"Generated {len(chapter_list)} chapters successfully"
            )
        
        # Generate and save lessons for each chapter using parallel processing
        total_lessons = 0
        chapter_lesson_plans = {}
        
        # Thread-safe lock for shared variables
        results_lock = threading.Lock()
        
        print(f"� Starting parallel processing of {len(created_chapters)} chapters...")
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=min(len(created_chapters), 4)) as executor:
            # Submit all chapter processing tasks
            future_to_chapter = {}
            for i, chapter in enumerate(created_chapters):
                chapter_item = chapter_list[i]  # Original chapter data for API call
                future = executor.submit(
                    process_single_chapter, 
                    chapter, 
                    chapter_item, 
                    course_structure_text, 
                    user_text, 
                    course_generation
                )
                future_to_chapter[future] = (chapter, chapter_item)
            
            # Collect results as they complete
            for future in as_completed(future_to_chapter):
                chapter, chapter_item = future_to_chapter[future]
                try:
                    result = future.result()
                    
                    # Thread-safe update of shared variables
                    with results_lock:
                        if result['error'] is None:
                            chapter_lesson_plans[f"chapter_{result['chapter_number']}"] = result['lesson_plan']
                            total_lessons += result['lessons_count']
                            print(f"✅ Completed Chapter {result['chapter_number']} with {result['lessons_count']} lessons")
                        else:
                            print(f"❌ Chapter {result['chapter_number']} failed: {result['error']}")
                            
                except Exception as exc:
                    print(f"❌ Chapter {chapter.chapter_number} generated an exception: {exc}")
                    traceback.print_exc()
        
        print(f"🎉 Parallel processing completed! Total lessons generated: {total_lessons}")
        
        # Create final project chapter
        final_project_result = create_final_project_chapter(course_generation, user_text, len(created_chapters) + 1)
        if final_project_result['success']:
            total_lessons += final_project_result['lessons_count']
            chapter_lesson_plans[f"chapter_{final_project_result['chapter_number']}"] = final_project_result['lesson_plan']
            print(f"✅ Added final project chapter with {final_project_result['lessons_count']} lesson")
        else:
            print(f"❌ Failed to create final project chapter: {final_project_result['error']}")
        
        # Compile final course data
        final_course_data = {
            "original_prompt": user_text,
            "overall_lesson_plan": chapter_list,
            "chapter_lesson_plans": chapter_lesson_plans
        }
        
        # Final update to course generation
        with transaction.atomic():
            course_generation.total_lessons = total_lessons
            course_generation.total_chapters = len(created_chapters) + (1 if final_project_result['success'] else 0)  # Include final project chapter if successful
            course_generation.status = 'completed'
            course_generation.completed_at = timezone.now()
            course_generation.course_data_json = final_course_data
            course_generation.save()
            
            GenerationLog.objects.create(
                course_generation=course_generation,
                step="generation_completed",
                status="completed",
                message=f"Course generation completed successfully. {course_generation.total_chapters} chapters, {course_generation.total_lessons} lessons."
            )
        
        print(f"✅ [{timestamp}] Course generation completed successfully! ID: {course_generation.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Course generated successfully!',
            'course_generation_id': course_generation.id,
            'total_chapters': course_generation.total_chapters,
            'total_lessons': course_generation.total_lessons,
            'result': f"Generated {course_generation.total_chapters} chapters with {course_generation.total_lessons} lessons",
            'course_data': final_course_data  # Still send to frontend
        })
        
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"❌ [{timestamp}] Error processing request: {str(e)}")
        
        # Log the error if we have a course_generation object
        if course_generation:
            try:
                with transaction.atomic():
                    course_generation.status = 'failed'
                    course_generation.save()
                    
                    GenerationLog.objects.create(
                        course_generation=course_generation,
                        step="generation_error",
                        status="failed",
                        level="error",
                        message=f"Course generation failed: {str(e)}"
                    )
            except Exception as log_error:
                print(f"❌ Failed to log error: {str(log_error)}")
            
        return JsonResponse({
            'success': False,
            'error': str(e),
            'course_generation_id': course_generation.id if course_generation else None
        }, status=400)


def take_quiz(request, quiz_id):
    """Display the quiz for the user to take."""
    try:
        quiz = MultipleChoiceQuiz.objects.get(id=quiz_id)
        sidebar_ctx = _sidebar_context_for_lesson(quiz.lesson)
        ctx = {
            'quiz': quiz,
            'questions': quiz.quiz_data.get('questions', [])
        }
        ctx.update(sidebar_ctx)
        return render(request, 'generation/take_quiz.html', ctx)
    except MultipleChoiceQuiz.DoesNotExist:
        return render(request, 'generation/error.html', {
            'error': 'Quiz not found'
        })


@require_http_methods(["POST"])
def submit_quiz(request, quiz_id):
    """Process quiz submission and store results."""
    try:
        quiz = MultipleChoiceQuiz.objects.get(id=quiz_id)
        user_answers = {}
        
        # Collect user answers from POST data
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_index = int(key.replace('question_', ''))
                user_answers[question_index] = value
        
        # Calculate results
        questions = quiz.quiz_data.get('questions', [])
        results = []
        correct_count = 0
        
        for i, question in enumerate(questions):
            user_answer = user_answers.get(i, '')
            correct_answer = question.get('correct_answer', '')
            is_correct = user_answer == correct_answer
            
            if is_correct:
                correct_count += 1
            
            results.append({
                'question_index': i,
                'question': question.get('question', ''),
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'explanation': question.get('explanation', '')
            })
        
        # Store the attempt
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user_answers=user_answers,
            results=results,
            score=correct_count,
            total_questions=len(questions)
        )
        
        # Calculate percentage
        percentage = round((correct_count / len(questions)) * 100) if len(questions) > 0 else 0
        
        # Mark lesson complete if score >= 70%
        try:
            if len(questions) > 0 and (correct_count / len(questions)) >= 0.1:
                quiz.lesson.is_complete = True
                quiz.lesson.save(update_fields=['is_complete'])
        except Exception:
            pass

        ctx = {
            'quiz': quiz,
            'attempt': attempt,
            'results': results,
            'score': correct_count,
            'total': len(questions),
            'percentage': percentage
        }
        ctx.update(_sidebar_context_for_lesson(quiz.lesson))
        return render(request, 'generation/quiz_results.html', ctx)
        
    except MultipleChoiceQuiz.DoesNotExist:
        return render(request, 'generation/error.html', {
            'error': 'Quiz not found'
        })
    except Exception as e:
        return render(request, 'generation/error.html', {
            'error': f'An error occurred: {str(e)}'
        })


def search_youtube_for_lesson(lesson):
    from .models import YouTubeVideo  
    try:
        if lesson.lesson_type != 'vid':
            print('YouTube search only available for learning lesson types.')
            return
        lesson_dict = {
            'lesson_name': lesson.lesson_name,
            'lesson_description': lesson.lesson_description,
            'lesson_details': lesson.lesson_details,
        }
        query = generate_youtube_query(lesson_dict)
        yt_results = search_youtube(query)
        print(f"YouTube search completed for lesson {lesson.id}")
        # Store top videos
        items = yt_results.get('items', [])
        for item in items:
            vid = item['id'].get('videoId')
            snippet = item.get('snippet', {})
            if not vid:
                continue
            YouTubeVideo.objects.update_or_create(
                lesson=lesson,
                video_id=vid,
                defaults={
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'thumbnail_url': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                    'channel_title': snippet.get('channelTitle', ''),
                    'published_at': snippet.get('publishedAt', None),
                    'video_url': f'https://www.youtube.com/watch?v={vid}',
                    'raw_data': item
                }
            )
        return yt_results
    except Exception as e:
        print(f"Error in YouTube search: {str(e)}")
        return None
    
def generate_programming_exercise(lesson):
    """Generate a programming project for a given lesson using Cerebras API."""
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """
                    You are an expert programming instructor and curriculum designer.
                    Your task is to create a programming exercise based on the provided lesson content.

                    Create a practical programming project that reinforces the concepts from the lesson.
                    The project should include:
                    - Starter code files (as a dictionary of filename -> code content)
                    - A grading methodology: either 'ai_review' for AI-based code review or 'terminal_matching' for output comparison
                    - If terminal_matching is chosen, provide the expected terminal output

                    The starter code should be minimal but functional, allowing students to build upon it.
                    Choose terminal_matching only for simple programs with predictable output.
                    Use ai_review for more complex projects requiring code quality assessment.

                    Output format: Return ONLY valid JSON in the following structure:
                    {
                        "starter_files": {
                            "main.py": "print('Hello World')",
                            "utils.py": "# Helper functions"
                        },
                        "grading_method": "ai_review",
                        "expected_output": "Hello World\\n"
                    }

                    For terminal_matching, expected_output should be the exact output the program should produce.
                    For ai_review, expected_output can be empty or omitted.
                    DO NOT include any additional text outside the JSON.
                """,
            },
            {
                "role": "user",
                "content": f"""
                    Lesson Name: {lesson.lesson_name}
                    Lesson Description: {lesson.lesson_description}
                    Lesson Details: {lesson.lesson_details}
                    Lesson Goals: {lesson.lesson_goals}
                    Lesson Guidelines: {lesson.lesson_guidelines}
                """,
            }
        ],
        model="qwen-3-coder-480b",
    )

    response_content = chat_completion.choices[0].message.content
    try:
        project_data = json.loads(response_content.strip())
    except json.JSONDecodeError as e:
        print(f"JSON decode error in generate_programming_exercise: {e}")
        print(f"Response content length: {len(response_content)}")
        # Try to extract JSON between first { and last }
        start = response_content.find('{')
        end = response_content.rfind('}')
        if start != -1 and end > start:
            project_data = json.loads(response_content[start:end+1])
        else:
            raise ValueError("No JSON object found in response")
    
    # Create the Project object
    project = Project.objects.create(
        lesson=lesson,
        name=f"Exercise for {lesson.lesson_name}",
        description=f"Programming exercise: {lesson.lesson_description}",
        grading_method=project_data.get('grading_method', 'ai_review'),
        expected_output=project_data.get('expected_output', '')
    )
    
    # Create File objects for starter files
    starter_files = project_data.get('starter_files', {})
    for filename, content in starter_files.items():
        File.objects.create(
            project=project,
            name=filename,
            relative_path=filename,
            content=content
        )

    print(f"✅ Generated programming exercise for Lesson {lesson.lesson_number} with {len(starter_files)} starter files")
    
    return project

def lesson_youtube(request, lesson_id):
    """Display the YouTube video(s) for a lesson."""
    from .models import GeneratedLesson
    lesson = GeneratedLesson.objects.get(id=lesson_id)
    # Mark as complete when user visits the video lesson
    if not lesson.is_complete:
        try:
            lesson.is_complete = True
            lesson.save(update_fields=['is_complete'])
        except Exception:
            pass
    ctx = {'lesson': lesson}
    ctx.update(_sidebar_context_for_lesson(lesson))
    return render(request, 'generation/youtube_vid.html', ctx)

def load_lesson_project(request, lesson_id):
    """Load a programming project for a lesson into the code editor."""
    workspace_path = '/Users/aditya/Documents/Programming/Hackathon/PennApps/pennapps25/workspace-python/'
    
    # Get the lesson
    lesson = get_object_or_404(GeneratedLesson, id=lesson_id)
    
    # Get the associated project
    try:
        project = lesson.programming_project
    except Project.DoesNotExist:
        # If no project exists, create a default one
        project = Project.objects.create(
            lesson=lesson,
            name=f"Exercise for {lesson.lesson_name}",
            description=f"Programming exercise: {lesson.lesson_description}",
            grading_method='ai_review'
        )
        # Create a default starter file
        File.objects.create(
            project=project,
            name='main.py',
            relative_path='main.py',
            content="# Write your code here\nprint('Hello World')"
        )
    
    # Clear existing files in workspace (except venv)
    if os.path.exists(workspace_path):
        items = os.listdir(workspace_path)
        print(f"Clearing workspace: {items}")
        for item in items:
            if item != 'venv':
                item_path = os.path.join(workspace_path, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
    
    # Load project files
    files = project.files.all()
    print(f"Loading project '{project.name}' with {files.count()} files")
    
    # Create all the project files
    for file_obj in files:
        file_path = os.path.join(workspace_path, file_obj.relative_path)
        
        # Create directory structure if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write file content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_obj.content)
            
        print(f"Created file: {file_obj.relative_path}")
    
    context = {
        'lesson': lesson,
        'project': project,
        'files': files
    }
    context.update(_sidebar_context_for_lesson(lesson))
    
    return render(request, 'generation/code_editor.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def submit_code_correction(request, lesson_id):
    """Submit code for AI correction."""
    try:
        lesson = get_object_or_404(GeneratedLesson, id=lesson_id)
        project = lesson.programming_project
        
        # Get current code from workspace - read ALL files
        workspace_path = '/Users/aditya/Documents/Programming/Hackathon/PennApps/pennapps25/workspace-python/'
        all_files_content = {}
        
        # Read all Python files and other relevant files in the workspace
        if os.path.exists(workspace_path):
            # Directories to skip (common virtual env and cache directories)
            skip_dirs = {'venv', 'env', '.venv', '.env', '__pycache__', '.git', 'node_modules', 
                        '.pytest_cache', '.mypy_cache', '.tox', 'build', 'dist', '.eggs'}
            
            for root, dirs, files in os.walk(workspace_path):
                # Skip hidden directories, cache directories, and virtual environments
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in skip_dirs]
                
                for file in files:
                    # Skip files that are too large or not relevant for code analysis
                    if (file.endswith(('.py', '.txt', '.md', '.json', '.yaml', '.yml', '.cfg', '.ini')) and
                        not file.startswith('.') and 
                        not file.endswith(('.pyc', '.pyo', '.log'))):
                        
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, workspace_path)
                        
                        try:
                            # Check file size before reading (skip files larger than 50KB)
                            if os.path.getsize(file_path) > 50 * 1024:  # 50KB limit
                                continue
                                
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if content.strip() and len(content) < 10000:  # Only include files under 10KB
                                    all_files_content[relative_path] = content
                        except (UnicodeDecodeError, OSError, PermissionError):
                            # Skip binary files, permission issues, or files with encoding issues
                            continue
        
        if not all_files_content:
            return JsonResponse({
                'success': False,
                'message': 'No code files found to correct'
            })
        
        # Create a comprehensive code summary for analysis with size limit
        # Prioritize files by importance (main.py first, then .py files, then others)
        file_priority = []
        for file_path, content in all_files_content.items():
            if file_path == 'main.py':
                priority = 0
            elif file_path.endswith('.py'):
                priority = 1
            elif file_path.endswith(('.json', '.yaml', '.yml')):
                priority = 2
            else:
                priority = 3
            file_priority.append((priority, file_path, content))
        
        # Sort by priority
        file_priority.sort(key=lambda x: x[0])
        
        code_summary = "PROJECT FILES:\n" + "="*50 + "\n\n"
        total_content_size = 0
        max_content_size = 30000  # 30KB limit for total content
        files_included = 0
        
        for priority, file_path, content in file_priority:
            file_section = f"FILE: {file_path}\n" + "-"*30 + "\n" + content + "\n\n"
            
            # Check if adding this file would exceed our limit
            if total_content_size + len(file_section) > max_content_size:
                remaining_files = len(file_priority) - files_included
                code_summary += f"\n[NOTE: {remaining_files} additional files truncated to stay within analysis limits]\n"
                break
                
            code_summary += file_section
            total_content_size += len(file_section)
            files_included += 1
        
        print(f"📁 Code correction analyzing {files_included}/{len(all_files_content)} files, total size: {total_content_size} characters")
        included_files = [item[1] for item in file_priority[:files_included]]
        print(f"📄 Files included: {included_files}")
        
        # Use Cerebras API to correct the code
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"""
                    You are an expert programming instructor. Your task is to analyze and correct student code for a programming exercise that may contain multiple files.

                    Lesson Context:
                    - Lesson: {lesson.lesson_name}
                    - Description: {lesson.lesson_description}
                    - Details: {lesson.lesson_details}
                    - Goals: {lesson.lesson_goals}

                    The student has submitted a complete project with multiple files. Your task is to:
                    1. Analyze ALL files in the project comprehensively
                    2. Identify syntax errors, logical errors, architectural issues, and improvements needed across all files
                    3. Check for proper file organization, imports, and inter-file dependencies
                    4. Provide corrected code for files that need changes
                    5. Explain what was wrong and how you fixed it across the entire project
                    6. Suggest improvements, best practices, and architectural recommendations
                    7. Give an overall PASS/FAIL assessment based on whether the complete project meets lesson requirements

                    Return your response as JSON with the following structure:
                    {{
                        "pass_fail": "PASS" or "FAIL",
                        "corrected_code": {{
                            "main.py": "corrected main file content",
                            "utils.py": "corrected utils file content",
                            "other_file.py": "corrected content for other files as needed"
                        }},
                        "explanation": "detailed explanation of changes across all files and overall project structure",
                        "issues_found": ["list of issues identified across all files"],
                        "suggestions": ["list of improvement suggestions for the entire project"],
                        "file_analysis": {{
                            "main.py": "specific analysis and issues for this file",
                            "utils.py": "specific analysis and issues for this file"
                        }}
                    }}

                    For PASS/FAIL assessment:
                    - PASS: All files work together properly, no critical errors, meets core lesson objectives
                    - FAIL: Critical errors in any file, improper file organization, or doesn't meet basic lesson requirements

                    Be comprehensive in your analysis - look at the entire project as a cohesive system.
                    Be helpful, educational, and encouraging. Focus on teaching why changes are needed.
                    Only include files in corrected_code that actually need corrections.
                    """,
                },
                {
                    "role": "user",
                    "content": f"Here is my complete project for the lesson '{lesson.lesson_name}':\n\n{code_summary}"
                }
            ],
            model="qwen-3-coder-480b",
        )

        response_content = chat_completion.choices[0].message.content
        
        try:
            correction_data = json.loads(response_content.strip())
        except json.JSONDecodeError:
            # Try to extract JSON
            start = response_content.find('{')
            end = response_content.rfind('}')
            if start != -1 and end > start:
                correction_data = json.loads(response_content[start:end+1])
            else:
                correction_data = {
                    "pass_fail": "UNKNOWN",
                    "corrected_code": response_content,
                    "explanation": "Code analysis completed",
                    "issues_found": ["Analysis provided"],
                    "suggestions": ["Review the corrected code"],
                    "grade": "N/A"
                }
        
        # Update files with corrected code
        if 'corrected_code' in correction_data:
            # If correction_data contains file-specific corrections, apply them
            if isinstance(correction_data['corrected_code'], dict):
                # Multiple files corrected
                for file_path, corrected_content in correction_data['corrected_code'].items():
                    full_file_path = os.path.join(workspace_path, file_path)
                    os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
                    with open(full_file_path, 'w', encoding='utf-8') as f:
                        f.write(corrected_content)
            else:
                # Single main file correction (fallback)
                main_file_path = os.path.join(workspace_path, 'main.py')
                if os.path.exists(main_file_path):
                    with open(main_file_path, 'w', encoding='utf-8') as f:
                        f.write(correction_data['corrected_code'])
        
        # If correction indicates PASS, mark lesson complete
        try:
            pass_fail_value = None
            if isinstance(correction_data, dict):
                pass_fail_value = correction_data.get('pass_fail')
            if isinstance(pass_fail_value, str) and pass_fail_value.upper() == 'PASS':
                if not lesson.is_complete:
                    lesson.is_complete = True
                    lesson.save(update_fields=['is_complete'])
                lesson_completed = True
            else:
                lesson_completed = False
        except Exception:
            lesson_completed = False

        return JsonResponse({
            'success': True,
            'correction': correction_data,
            'lesson_completed': lesson_completed
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing code correction: {str(e)}'
        }, status=500)


# --------------- Additional lesson pages ---------------
def lesson_article(request, lesson_id):
    """Display generated article content for a lesson (art)."""
    lesson = get_object_or_404(GeneratedLesson, id=lesson_id)
    article = getattr(lesson, 'article', None)
    # Mark as complete on article view
    if not lesson.is_complete:
        try:
            lesson.is_complete = True
            lesson.save(update_fields=['is_complete'])
        except Exception:
            pass
    ctx = {'lesson': lesson, 'article': article}
    ctx.update(_sidebar_context_for_lesson(lesson))
    return render(request, 'generation/article.html', ctx)


def lesson_external(request, lesson_id):
    """Display an external article link for a lesson (ext)."""
    lesson = get_object_or_404(GeneratedLesson, id=lesson_id)
    external = getattr(lesson, 'external_article', None)
    # Mark as complete on external lesson view
    if not lesson.is_complete:
        try:
            lesson.is_complete = True
            lesson.save(update_fields=['is_complete'])
        except Exception:
            pass
    ctx = {'lesson': lesson, 'external': external}
    ctx.update(_sidebar_context_for_lesson(lesson))
    return render(request, 'generation/external_article.html', ctx)


def generate_text_response_questions(lesson):
    """Generate 2-5 questions for text response lessons using Cerebras API."""
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """
                    You are an expert educational content creator specializing in creating thoughtful questions 
                    that test comprehension and application of lesson material.

                    Your task is to create 2-5 questions based on the provided lesson content that require 
                    text-based responses from students. These questions should:
                    - Test understanding of key concepts from the lesson
                    - Encourage critical thinking and application
                    - Be answerable based on the lesson content
                    - Vary in difficulty and question type
                    - Include both factual and analytical questions

                    For each question, provide an optimal answer that demonstrates what a good student 
                    response would look like.

                    Output format: Return ONLY valid JSON in the following structure:
                    {
                        "questions": [
                            {
                                "question_number": 1,
                                "question": "What are the main benefits of using version control in software development?",
                                "optimal_answer": "Version control provides several key benefits including: tracking changes over time, enabling collaboration among team members, maintaining backup history, allowing easy rollback to previous versions, and enabling branching for feature development."
                            },
                            {
                                "question_number": 2,
                                "question": "Explain how you would implement error handling in a Python function.",
                                "optimal_answer": "Error handling in Python can be implemented using try-except blocks. You would wrap potentially problematic code in a try block, catch specific exceptions in except blocks, optionally use finally for cleanup code, and consider logging errors for debugging purposes."
                            }
                        ]
                    }

                    Generate between 2-5 questions. Make them diverse and comprehensive.
                    DO NOT include any additional text outside the JSON.
                """,
            },
            {
                "role": "user",
                "content": f"""
                    Lesson Name: {lesson.lesson_name}
                    Lesson Description: {lesson.lesson_description}
                    Lesson Details: {lesson.lesson_details}
                    Lesson Goals: {lesson.lesson_goals}
                    Lesson Guidelines: {lesson.lesson_guidelines}
                """,
            }
        ],
        model="qwen-3-coder-480b",
    )

    response_content = chat_completion.choices[0].message.content
    try:
        questions_data = json.loads(response_content.strip())
    except json.JSONDecodeError as e:
        print(f"JSON decode error in generate_text_response_questions: {e}")
        print(f"Response content length: {len(response_content)}")
        # Try to extract JSON between first { and last }
        start = response_content.find('{')
        end = response_content.rfind('}')
        if start != -1 and end > start:
            json_str = response_content[start:end+1].strip()
            try:
                questions_data = json.loads(json_str)
            except json.JSONDecodeError as e2:
                print(f"Failed to parse extracted JSON: {e2}")
                raise ValueError("Unable to parse questions JSON")
        else:
            raise ValueError("No JSON object found in response")
    
    # Save questions to the database using the new model
    with transaction.atomic():
        # Delete existing questions for this lesson
        TextResponseQuestion.objects.filter(lesson=lesson).delete()
        
        # Create new questions
        questions = questions_data.get('questions', [])
        for question_data in questions:
            TextResponseQuestion.objects.create(
                lesson=lesson,
                question_number=question_data.get('question_number', 1),
                question=question_data.get('question', ''),
                optimal_answer=question_data.get('optimal_answer', '')
            )
    
    print(f"✅ Generated and saved {len(questions)} text response questions for Lesson {lesson.lesson_number} in Chapter {lesson.chapter.chapter_number}")
    
    return questions_data


def grade_text_responses(lesson, user_answers):
    """Grade user text responses using Cerebras API."""
    # Get the questions for this lesson
    questions = TextResponseQuestion.objects.filter(lesson=lesson).order_by('question_number')
    
    if not questions.exists():
        raise ValueError("No questions found for this lesson")
    
    # Prepare the grading prompt
    grading_data = []
    for question in questions:
        question_num = str(question.question_number)
        user_answer = user_answers.get(question_num, "")
        
        grading_data.append({
            "question_number": question.question_number,
            "question": question.question,
            "optimal_answer": question.optimal_answer,
            "user_answer": user_answer
        })
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """
                    You are an expert educational assessor and grader. Your task is to evaluate student text responses to questions.

                    For each question, you will be provided with:
                    - The original question
                    - The optimal answer (reference answer)
                    - The student's actual answer

                    Grade each answer on a scale of 0-100 based on:
                    - Accuracy: How correct is the information?
                    - Completeness: Does it cover the key points?
                    - Understanding: Does the student demonstrate comprehension?
                    - Clarity: Is the answer well-structured and clear?

                    Provide constructive feedback explaining what was good and what could be improved.

                    Output format: Return ONLY valid JSON in the following structure:
                    {
                        "grades": [
                            {
                                "question_number": 1,
                                "score": 85,
                                "feedback": "Good understanding of the core concepts. You correctly identified the main benefits but could have elaborated more on collaboration aspects.",
                                "strengths": ["Accurate information", "Clear structure"],
                                "improvements": ["Add more detail on team collaboration", "Include specific examples"]
                            },
                            {
                                "question_number": 2,
                                "score": 92,
                                "feedback": "Excellent response with clear examples and comprehensive coverage of error handling techniques.",
                                "strengths": ["Complete coverage", "Good examples", "Clear explanation"],
                                "improvements": ["Minor: Could mention logging best practices"]
                            }
                        ],
                        "overall_score": 88.5,
                        "overall_feedback": "Strong performance overall. Good understanding of key concepts with room for more detailed explanations."
                    }

                    Be fair, constructive, and encouraging in your feedback.
                    DO NOT include any additional text outside the JSON.
                """,
            },
            {
                "role": "user",
                "content": f"""
                    Lesson: {lesson.lesson_name}
                    
                    Please grade the following responses:
                    
                    {json.dumps(grading_data, indent=2)}
                """,
            }
        ],
        model="qwen-3-coder-480b",
    )

    response_content = chat_completion.choices[0].message.content
    try:
        grades_data = json.loads(response_content.strip())
    except json.JSONDecodeError as e:
        print(f"JSON decode error in grade_text_responses: {e}")
        print(f"Response content length: {len(response_content)}")
        # Try to extract JSON between first { and last }
        start = response_content.find('{')
        end = response_content.rfind('}')
        if start != -1 and end > start:
            json_str = response_content[start:end+1].strip()
            try:
                grades_data = json.loads(json_str)
            except json.JSONDecodeError as e2:
                print(f"Failed to parse extracted JSON: {e2}")
                # Create fallback grades
                fallback_grades = {
                    "grades": [],
                    "overall_score": 75.0,
                    "overall_feedback": "Your responses have been received and reviewed."
                }
                for question in questions:
                    question_num = str(question.question_number)
                    if question_num in user_answers and user_answers[question_num].strip():
                        fallback_grades["grades"].append({
                            "question_number": question.question_number,
                            "score": 75,
                            "feedback": "Your response shows understanding of the topic.",
                            "strengths": ["Shows engagement with the material"],
                            "improvements": ["Consider adding more specific details"]
                        })
                return fallback_grades
        else:
            raise ValueError("No JSON object found in response")
    
    print(f"✅ Graded {len(grades_data.get('grades', []))} responses for Lesson {lesson.lesson_number} in Chapter {lesson.chapter.chapter_number}")
    
    return grades_data


def lesson_text_response(request, lesson_id):
    """Display text response questions for a lesson (txt)."""
    lesson = get_object_or_404(GeneratedLesson, id=lesson_id)
    
    # Check if questions exist in the database
    questions = TextResponseQuestion.objects.filter(lesson=lesson).order_by('question_number')
    
    # Generate questions if they don't exist yet
    if not questions.exists():
        try:
            generate_text_response_questions(lesson)
            # Reload questions from database
            questions = TextResponseQuestion.objects.filter(lesson=lesson).order_by('question_number')
        except Exception as e:
            print(f"Error generating text response questions: {str(e)}")
            # Create a fallback question
            TextResponseQuestion.objects.create(
                lesson=lesson,
                question_number=1,
                question=f"Summarize the key concepts from the lesson: {lesson.lesson_name}",
                optimal_answer="Please provide a comprehensive summary based on the lesson content."
            )
            questions = TextResponseQuestion.objects.filter(lesson=lesson).order_by('question_number')
    
    ctx = {
        'lesson': lesson, 
        'questions': questions
    }
    ctx.update(_sidebar_context_for_lesson(lesson))
    return render(request, 'generation/text_response.html', ctx)


@csrf_exempt
@require_http_methods(["POST"])
def submit_text_responses(request, lesson_id):
    """Submit and grade text responses for a lesson."""
    try:
        lesson = get_object_or_404(GeneratedLesson, id=lesson_id)
        
        # Parse the submitted answers
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            user_answers = data.get('answers', {})
        else:
            user_answers = {}
            for key, value in request.POST.items():
                if key.startswith('answer-'):
                    question_num = key.replace('answer-', '')
                    user_answers[question_num] = value
        
        # Validate that we have answers
        if not user_answers or all(not answer.strip() for answer in user_answers.values()):
            return JsonResponse({
                'success': False,
                'message': 'Please provide at least one answer before submitting.'
            }, status=400)
        
        # Grade the responses using Cerebras API
        try:
            grades_data = grade_text_responses(lesson, user_answers)
        except Exception as grading_error:
            print(f"Error grading responses: {str(grading_error)}")
            return JsonResponse({
                'success': False,
                'message': f'Error grading responses: {str(grading_error)}'
            }, status=500)
        
        # Save the submission to database
        with transaction.atomic():
            submission = TextResponseSubmission.objects.create(
                lesson=lesson,
                user=request.user if request.user.is_authenticated else None,
                user_answers=user_answers,
                grades=grades_data,
                total_score=grades_data.get('overall_score', 0),
                total_questions=len(user_answers),
                graded_at=timezone.now()
            )
        
        # Mark lesson complete if overall score >= 70
        try:
            if grades_data.get('overall_score', 0) >= 70:
                lesson.is_complete = True
                lesson.save(update_fields=['is_complete'])
        except Exception:
            pass

        print(f"✅ Saved text response submission for Lesson {lesson.lesson_number}, Submission ID: {submission.id}")
        
        return JsonResponse({
            'success': True,
            'submission_id': submission.id,
            'grades': grades_data,
            'message': 'Your responses have been submitted and graded successfully!'
        })
        
    except Exception as e:
        print(f"Error processing text response submission: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)


def course_detail(request, course_id):
    """Display course details with all chapters and lessons."""
    try:
        course_generation = get_object_or_404(CourseGeneration, id=course_id)
        
        # Get all chapters with their lessons
        chapters = (GeneratedChapter.objects
                   .filter(course_generation=course_generation)
                   .prefetch_related('lessons', 'lessons__quiz', 'lessons__article', 'lessons__external_article')
                   .order_by('chapter_number'))
        
        # Calculate totals
        total_lessons = sum(chapter.lessons.count() for chapter in chapters)
        total_chapters = chapters.count()
        
        # Get lesson type stats
        lesson_type_counts = {}
        for chapter in chapters:
            for lesson in chapter.lessons.all():
                lesson_type = lesson.lesson_type
                lesson_type_counts[lesson_type] = lesson_type_counts.get(lesson_type, 0) + 1
        
        # Calculate completion percentage (for now, just based on status)
        completion_percentage = 100 if course_generation.status == 'completed' else 0
        
        context = {
            'course_generation': course_generation,
            'chapters': chapters,
            'total_chapters': total_chapters,
            'total_lessons': total_lessons,
            'lesson_type_counts': lesson_type_counts,
            'completion_percentage': completion_percentage,
        }
        
        return render(request, 'generation/course_detail.html', context)
        
    except CourseGeneration.DoesNotExist:
        return render(request, 'generation/error.html', {
            'error': 'Course not found'
        })


def course_list(request):
    """Display all generated courses."""
    courses = CourseGeneration.objects.all().order_by('-created_at')
    
    context = {
        'courses': courses
    }
    
    return render(request, 'generation/course_list.html', context)


def generate_ai_code_feedback(code_content, file_name="main.py", lesson_context=""):
    """Generate AI feedback for code content using Cerebras API."""
    try:
        messages = [
            {
                "role": "system",
                "content": """
                    You are an expert programming mentor and code reviewer. Your task is to analyze the provided code 
                    and give constructive, helpful feedback to help a student improve their programming skills.

                    Provide feedback in the following categories when relevant:
                    1. Code Quality & Best Practices
                    2. Potential Bugs or Issues
                    3. Performance Optimizations
                    4. Code Style & Readability
                    5. Architecture & Design
                    6. Encouragement & Positive Reinforcement

                    Format your response as a JSON object with the following structure:
                    {
                        "feedback_items": [
                            {
                                "type": "improvement|bug|style|performance|architecture|encouragement",
                                "priority": 1-5,
                                "title": "Brief title of the feedback",
                                "message": "Detailed explanation and suggestion",
                                "line_reference": "Optional line number or code snippet reference"
                            }
                        ],
                        "overall_assessment": "Brief overall assessment of the code quality and progress"
                    }

                    Be encouraging and constructive. This is for a student learning to code, so balance criticism 
                    with positive reinforcement. Focus on the most important improvements first.
                    
                    DO NOT include any additional text outside the JSON.
                """,
            },
            {
                "role": "user",
                "content": f"""
                    Please analyze this code and provide feedback:
                    
                    File: {file_name}
                    Lesson Context: {lesson_context}
                    
                    Code:
                    ```
                    {code_content}
                    ```
                """,
            }
        ]
        
        # Try primary client first
        try:
            print(f"🔄 Generating AI feedback for {file_name} with primary Cerebras client...")
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="qwen-3-coder-480b",
            )
            print("✅ Primary client succeeded for AI feedback")
        except Exception as e:
            print(f"❌ Primary client failed for AI feedback: {str(e)}")
            try:
                print(f"🔄 Retrying AI feedback with secondary Cerebras client...")
                chat_completion = second_client.chat.completions.create(
                    messages=messages,
                    model="qwen-3-coder-480b",
                )
                print("✅ Secondary client succeeded for AI feedback")
            except Exception as e2:
                print(f"❌ Secondary client also failed for AI feedback: {str(e2)}")
                # Return fallback feedback
                return {
                    "feedback_items": [
                        {
                            "type": "encouragement",
                            "priority": 3,
                            "title": "Keep coding!",
                            "message": "You're making great progress! Keep working on your implementation.",
                            "line_reference": ""
                        }
                    ],
                    "overall_assessment": "AI feedback temporarily unavailable, but you're doing great!"
                }

        response_content = chat_completion.choices[0].message.content.strip()
        
        try:
            feedback_data = json.loads(response_content)
            return feedback_data
        except json.JSONDecodeError as e:
            print(f"JSON decode error in AI feedback: {e}")
            # Try to extract JSON between first { and last }
            start = response_content.find('{')
            end = response_content.rfind('}')
            if start != -1 and end > start:
                try:
                    feedback_data = json.loads(response_content[start:end+1])
                    return feedback_data
                except json.JSONDecodeError:
                    pass
            
            # Return fallback feedback if JSON parsing fails
            return {
                "feedback_items": [
                    {
                        "type": "encouragement",
                        "priority": 3,
                        "title": "Keep going!",
                        "message": "Your code is being processed. Continue working and the feedback will improve!",
                        "line_reference": ""
                    }
                ],
                "overall_assessment": "Code analysis in progress..."
            }
            
    except Exception as e:
        print(f"❌ Error generating AI feedback: {str(e)}")
        return {
            "feedback_items": [
                {
                    "type": "encouragement",
                    "priority": 3,
                    "title": "Technical difficulty",
                    "message": "Feedback system temporarily unavailable, but keep coding!",
                    "line_reference": ""
                }
            ],
            "overall_assessment": "System temporarily unavailable"
        }


@csrf_exempt
@require_http_methods(["POST"])
def get_ai_feedback(request):
    """API endpoint to get AI feedback for code content."""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            return JsonResponse({'error': 'Content-Type must be application/json'}, status=400)
        
        code_content = data.get('code_content', '')
        file_name = data.get('file_name', 'main.py')
        lesson_id = data.get('lesson_id')
        
        if not code_content.strip():
            return JsonResponse({
                'feedback_items': [
                    {
                        "type": "encouragement",
                        "priority": 2,
                        "title": "Start coding!",
                        "message": "Begin by writing some code and I'll provide helpful feedback as you work.",
                        "line_reference": ""
                    }
                ],
                'overall_assessment': "Ready to help you code!"
            })
        
        # Get lesson context if lesson_id provided
        lesson_context = ""
        if lesson_id:
            try:
                lesson = GeneratedLesson.objects.get(id=lesson_id)
                lesson_context = f"Lesson: {lesson.lesson_name} - {lesson.lesson_description}"
            except GeneratedLesson.DoesNotExist:
                pass
        
        # Generate AI feedback
        feedback = generate_ai_code_feedback(code_content, file_name, lesson_context)

        # If lesson provided and feedback indicates PASS, mark lesson complete
        try:
            if lesson_id:
                lesson = GeneratedLesson.objects.get(id=lesson_id)
                pass_fail = feedback.get('pass_fail') if isinstance(feedback, dict) else None
                # Some responses may have nested fields; handle common cases
                if isinstance(pass_fail, str) and pass_fail.upper() == 'PASS':
                    lesson.is_complete = True
                    lesson.save(update_fields=['is_complete'])
        except Exception:
            pass
        
        return JsonResponse(feedback)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"❌ Error in get_ai_feedback: {str(e)}")
        return JsonResponse({
            'error': 'Internal server error',
            'feedback_items': [
                {
                    "type": "encouragement",
                    "priority": 3,
                    "title": "Keep coding!",
                    "message": "Feedback system temporarily unavailable, but you're doing great!",
                    "line_reference": ""
                }
            ],
            'overall_assessment': "System temporarily unavailable"
        }, status=500)