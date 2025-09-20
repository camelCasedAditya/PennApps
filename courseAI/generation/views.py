from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime
from cerebras.cloud.sdk import Cerebras
import dotenv  
import os
from .models import CourseGeneration, GeneratedChapter, GeneratedLesson, LessonType, GenerationLog
from django.db import transaction
from django.utils import timezone

dotenv.load_dotenv()  # Load environment variables from .env file
client = Cerebras(
    api_key=os.getenv('CEREBRAS_API_KEY'),
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
                    The maximum number of chapters is 20.
                    
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
    chapter_list = json.loads(response_content.strip())
    
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
                            - Maximum: 20 lessons  
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

                            4. Ensure coherence: The lessons should logically connect, flow naturally, and cover everything needed for the learner to master this chapter.  

                          5. Output Format: Return ONLY valid JSON in the following structure (no explanations, no extra text):  
                            
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
                        Generated text based lesson - Name: txt , ID: 2,
                        Multiple choice quiz - Name: mcq , ID: 3,
                        Interactive programming exercise - Name: int , ID: 4,
                        External article Reading- Name: art , ID: 5,
                        Conclusion and Summary - Name: sum, ID: 6,
                        external resource review - Name: ext, ID: 7
                        code - Name: code, ID: 8

                        6. DO NOT RETURN ANYTHING OTHER THAN THE JSON. NO EXPLANATIONS, NO EXTRA TEXT. ONLY THE RAW JSON.
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

    lesson_plan = json.loads(chat_completion.choices[0].message.content.strip())
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