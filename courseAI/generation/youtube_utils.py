import os
import requests
from cerebras.cloud.sdk import Cerebras
import dotenv

dotenv.load_dotenv()

client = Cerebras(api_key=os.getenv('CEREBRAS_API_KEY'))
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_SEARCH_URL = 'https://www.googleapis.com/youtube/v3/search'

def generate_youtube_query(lesson):
    """Use Cerebras API to generate a YouTube search query and relevant parameters for a lesson."""
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """
                    You are an expert educational content curator specializing in finding the best YouTube videos for learning. Your task is to generate a JSON object for a YouTube search API call to find the most relevant educational video, based on the lesson details provided.

                    The JSON should include:
                    - query: a concise search query string
                    - relevanceLanguage: the most relevant language code (ISO 639-1, e.g. 'en'), if possible
                    - regionCode: the most relevant country code (ISO 3166-1 alpha-2, e.g. 'US'), if possible
                    - videoCategoryId: the most relevant YouTube video category ID (as a string), if possible

                    The video must be a maximum of 20 minutes long. 
                    Only return the JSON object, no explanations or extra text.
                """,
            },
            {
                "role": "user",
                "content": f"""
                    Lesson Name: {lesson['lesson_name']}
                    Lesson Description: {lesson['lesson_description']}
                    Lesson Details: {lesson['lesson_details']}
                """,
            }
        ],
        model="qwen-3-coder-480b",
    )
    # Parse JSON from response
    import json
    result = chat_completion.choices[0].message.content.strip()
    try:
        params = json.loads(result)
    except json.JSONDecodeError as e:
        print(f"JSON decode error in generate_youtube_query: {e}")
        print(f"Response content length: {len(result)}")
        # Try to extract JSON between first { and last }
        start = result.find('{')
        end = result.rfind('}')
        if start != -1 and end > start:
            json_str = result[start:end+1].strip()
            try:
                params = json.loads(json_str)
            except json.JSONDecodeError as e2:
                print(f"Failed to parse extracted JSON: {e2}")
                params = {"query": result}
        else:
            params = {"query": result}
    return params

def search_youtube(query_params, max_results=5):
    """Search YouTube for videos matching the query, return the single best video (most relevant, then highest view or like count)."""
    params = {
        'part': 'snippet',
        'q': query_params.get('query', ''),
        'type': 'video',
        'maxResults': max_results,
        'key': YOUTUBE_API_KEY,
        'safeSearch': 'strict',
        'videoDuration': 'medium',
        'order': 'relevance',  # First, get most relevant
    }
    if 'relevanceLanguage' in query_params:
        params['relevanceLanguage'] = query_params['relevanceLanguage']
    if 'regionCode' in query_params:
        params['regionCode'] = query_params['regionCode']
    if 'videoCategoryId' in query_params:
        params['videoCategoryId'] = query_params['videoCategoryId']
    response = requests.get(YOUTUBE_SEARCH_URL, params=params)
    response.raise_for_status()
    data = response.json()
    items = data.get('items', [])
    if not items:
        return {'items': []}
    # Get video IDs
    video_ids = [item['id']['videoId'] for item in items if 'videoId' in item['id']]
    if not video_ids:
        return {'items': []}
    # Fetch statistics for these videos
    stats_url = 'https://www.googleapis.com/youtube/v3/videos'
    stats_params = {
        'part': 'statistics',
        'id': ','.join(video_ids),
        'key': YOUTUBE_API_KEY
    }
    stats_resp = requests.get(stats_url, params=stats_params)
    stats_resp.raise_for_status()
    stats_data = stats_resp.json()
    stats_map = {item['id']: item['statistics'] for item in stats_data.get('items', [])}
    # Attach stats to items
    for item in items:
        vid = item['id'].get('videoId')
        if vid and vid in stats_map:
            item['statistics'] = stats_map[vid]
    # Pick the best video (highest like count, fallback to view count, then first)
    def get_likes(item):
        try:
            return int(item.get('statistics', {}).get('likeCount', 0))
        except Exception:
            return 0
    def get_views(item):
        try:
            return int(item.get('statistics', {}).get('viewCount', 0))
        except Exception:
            return 0
    # Sort by like count, then view count
    items_sorted = sorted(items, key=lambda x: (get_likes(x), get_views(x)), reverse=True)
    best_item = items_sorted[0]
    return {'items': [best_item]}
