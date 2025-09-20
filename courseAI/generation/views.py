from django.shortcuts import render
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
from .models import CourseGeneration, GeneratedChapter, GeneratedLesson, LessonType, GenerationLog, MultipleChoiceQuiz, QuizAttempt, QuizAttempt, ArticleContent, YouTubeVideo, ExternalArticles
from django.db import transaction
from django.utils import timezone
from .youtube_utils import generate_youtube_query, search_youtube
from courses.models import Project, File

dotenv.load_dotenv()  # Load environment variables from .env file
client = Cerebras(
    api_key=os.getenv('CEREBRAS_API_KEY'),
    max_retries=5
)


def generation_form(request):
    """Display the course generation form."""
    return render(request, 'generation/form.html')


def chapter_list_create(input_prompt, exp):
    """Generate chapter list using Cerebras API."""
    chat_completion = client.chat.completions.create(
        messages=[
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
        ],
        model="qwen-3-coder-480b",
    )

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
                        Conclusion and Summary* (should only be the last lesson in chapter) - Name: sum, ID: 4,

                        Practice Lessons:
                        Interactive programming exercise - Name: int , ID: 5,
                        Multiple choice quiz - Name: mcq , ID: 6,
                        text response - Name: txt , ID: 7,
                        fill in the blank - Name: fib , ID: 8,
                        final project* (only at the end if there is enough learned) - Name: pro , ID: 9,

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
            # Hardcoded experience level as requested
            experience_level = "I know nothing, I don't even know how to run code or anything."
        else:
            user_text = request.POST.get('text', '')
            # Hardcoded experience level as requested
            experience_level = "I know nothing, I don't even know how to run code or anything."
        
        # Print the received text to the terminal
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"📝 [{timestamp}] Received text from frontend: {user_text}")
        print(f"📊 Full request data: {json.dumps({'text': user_text, 'experience': experience_level, 'timestamp': timestamp}, indent=2)}")
    
        # Create initial course generation record
        with transaction.atomic():
            course_generation = CourseGeneration.objects.create(
                user_prompt=user_text,
                experience_level=experience_level,
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
        
        chapter_list = chapter_list_create(user_text, experience_level)
        
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
        
        # Generate and save lessons for each chapter
        total_lessons = 0
        chapter_lesson_plans = {}
        
        for i, chapter in enumerate(created_chapters):
            print(f"🔄 Generating lessons for Chapter {chapter.chapter_number}...")
            
            GenerationLog.objects.create(
                course_generation=course_generation,
                step=f"lesson_generation_chapter_{chapter.chapter_number}",
                status="in_progress",
                message=f"Generating lessons for Chapter {chapter.chapter_number}"
            )
            
            # Generate lesson plan
            chapter_item = chapter_list[i]  # Original chapter data for API call
            lesson_plan = create_lesson(chapter_item, course_structure_text, user_text)
            chapter_lesson_plans[f"chapter_{chapter.chapter_number}"] = lesson_plan
            
            
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
                    total_lessons += 1
                
                GenerationLog.objects.create(
                    course_generation=course_generation,
                    step=f"lesson_generation_chapter_{chapter.chapter_number}",
                    status="completed",
                    message=f"Generated {len(lesson_plan)} lessons for Chapter {chapter.chapter_number}"
                )
            
            lessons = GeneratedLesson.objects.filter(chapter=chapter)
            for lesson in lessons:
                print(f"🔍 Processing lesson {lesson.lesson_number} with type: '{lesson.lesson_type}'")
                if lesson.lesson_type == 'mcq':
                    quiz = generate_quiz(lesson)
                    print(f"✅ Generated quiz for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}, Quiz ID: {quiz.id}")
                if lesson.lesson_type == "int":
                    generate_programming_exercise(lesson)
                if lesson.lesson_type == "vid":
                    search_youtube_for_lesson(lesson)  
                    print(f"✅ Prepared YouTube search for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}")
                if lesson.lesson_type == "ext":
                    print(f"🔍 Found EXT lesson type! Processing external article for lesson {lesson.lesson_number}")
                    print(f"🔍 Tavily API Key exists: {bool(os.getenv('TAVILY_API_KEY'))}")
                    source = get_best_source(f"{lesson.lesson_name}. {lesson.lesson_description} {lesson.lesson_details}")
                    print(f"🔍 get_best_source returned: {source}")
                    if source and source.get('url'):
                        ExternalArticles.objects.create(
                            lesson=lesson,
                            url=source['url']
                        )
                        print(f"✅ Saved external article URL for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}: {source['url']}")
                    else:
                        print(f"⚠️ No suitable external article found for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}")
                if lesson.lesson_type == "art":
                    article = ai_gen_article(lesson)
                    ArticleContent.objects.create(
                        lesson=lesson,
                        content=article
                    )
                    print(f"✅ Generated article for Lesson {lesson.lesson_number} in Chapter {chapter.chapter_number}")
            print(f"✅ Saved {len(lesson_plan)} lessons for Chapter {chapter.chapter_number}")
        
        # Compile final course data
        final_course_data = {
            "original_prompt": user_text,
            "overall_lesson_plan": chapter_list,
            "chapter_lesson_plans": chapter_lesson_plans
        }
        
        # Final update to course generation
        with transaction.atomic():
            course_generation.total_lessons = total_lessons
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
        return render(request, 'generation/take_quiz.html', {
            'quiz': quiz,
            'questions': quiz.quiz_data.get('questions', [])
        })
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
        
        return render(request, 'generation/quiz_results.html', {
            'quiz': quiz,
            'attempt': attempt,
            'results': results,
            'score': correct_count,
            'total': len(questions),
            'percentage': percentage
        })
        
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
    return render(request, 'generation/youtube_vid.html', {'lesson': lesson})