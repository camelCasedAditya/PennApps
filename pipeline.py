import json
import os
from cerebras.cloud.sdk import Cerebras
import dotenv  

dotenv.load_dotenv()  # Load environment variables from .env file

client = Cerebras(
    # This is the default and can be omitted
    api_key=os.getenv('CEREBRAS_API_KEY')
                      
                      )

def write_to_file(filename, content, json_format=False):
    if json_format:
        content = json.dumps(content, ensure_ascii=False, indent=4)
    with open(filename, "w", encoding="utf-8") as file:
        file.write(content)


def chapter_list_create(input, exp):
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
                "content": input,
            }
    ],
        model="llama-4-scout-17b-16e-instruct",
    )

    # Get the response content
    response_content = chat_completion.choices[0].message.content
    json_content = json.loads(response_content.strip())

    with open("chapter_list_create.json", "w", encoding="utf-8") as json_file:
        json.dump(json_content, json_file, ensure_ascii=False, indent=4)

    # Write the response to the text file
    write_to_file("chapter_list_create.txt", response_content)

    print(f"Chapter list saved to chapter_list_create.txt")
    return chat_completion
print(chapter_list_create("I want to code a financial tracking website.", "I know nothing, I don't even know how to run code or anything."))


def create_lesson(chapter_item, course_structure, prompt):
    """Create a lesson plan for a single chapter."""
    chapter_info = f"Chapter {chapter_item['chapter_number']}: {chapter_item['chapter_name']}\nDescription: {chapter_item['chapter_description']}\nDifficulty: {chapter_item['chapter_difficulty']}/10"
    
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

                            2. Randomize lesson structure: Do not use the same number or type of lessons across different chapters. Each chapter’s lessons should feel unique and adapted to the chapter’s content.  

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
                                "lesson_name": "",
                                "lesson_description": "",
                                "lesson_details": "",
                                "lesson_goals": ""
                        
                        Lesson options: 
                        Video - Name: vid, ID: 1,
                        Text response - Name: txt , ID: 2,
                        Multiple choice quiz - Name: mcq , ID: 3,
                        Interactive exercise - Name: int , ID: 4,
                        Article or reading - Name: art , ID: 5,
                        conclusion and summary - Name: sum, ID: 6,
                        external resource review - Name: ext, ID: 7
                        code - Name: code, ID: 8

                        6. DO NOT RETURN ANYTHING OTHER THAN THE JSON. NO EXPLANATIONS, NO EXTRA TEXT. ONLY THE RAW JSON.
                        """,
            }
        ],
        model="llama-4-scout-17b-16e-instruct",
    )

    write_to_file(f"lesson_plan_chapter_{chapter_item['chapter_number']}.txt", chat_completion.choices[0].message.content)
    print(f"Created lesson plan for Chapter {chapter_item['chapter_number']}: {chapter_item['chapter_name']}")
    return chat_completion

# Load the chapter list and create lesson plans for each chapter
with open("chapter_list_create.json", "r", encoding="utf-8") as json_file:
    chapter_list = json.load(json_file)

    input_prompt = "I want to create a business plan for my small business that sells flowers."
    
    # Create course structure summary for context
    course_structure = []
    for item in chapter_list:
        course_structure.append(f"Chapter {item['chapter_number']}: {item['chapter_name']} (Difficulty: {item['chapter_difficulty']}/10)")
    course_structure_text = "\n".join(course_structure)
    
    # Create lesson plan for each chapter
    for chapter in chapter_list:
        create_lesson(chapter, course_structure_text,input_prompt)
