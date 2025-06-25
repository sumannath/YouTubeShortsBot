import json
import logging
import os
import random
from google import genai
from config import constants


class StoryGenerator:
    def __init__(self):
        self.gemini_api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
        self.fallback_stories = constants.FALLBACK_STORIES

        # Story categories for variety
        self.story_categories = [
            "Paranormal/Supernatural", "Psychological Horror", "Creature Feature/Monster",
            "Home Invasion/Stalker", "Urban Legend/Folklore", "Techno-Horror",
            "Surprise/Twist Endings", "Dark Comedy/Absurdist", "Mystery (Micro-Mystery)",
            "Historical Horror"
        ]

    def get_story_from_gemini(self, category="Psychological Horror"):
        """Get a story from Google Gemini API"""
        if not self.gemini_api_key:
            logging.warning("No Gemini API key found, using fallback story")
            return self.get_fallback_story()

        client = genai.Client(api_key=self.gemini_api_key)

        prompt = f"""Generate an original, engaging {category} story that would work well for a YouTube Short. 
                    The story should be:
                    - about 50 words maximum
                    - Easy to read on screen
                    - Not from any famous person (original)
                    - The story should have an immediate punch

                    Return the title and the story text as json with key 'title' and 'story' respectively, nothing else."""

        try:
            logging.info(f"Fetching story from Gemini for category: {category}...")
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            story_json = response.text
            logging.info(f"Received response from Gemini")

            if story_json.startswith('```json'):
                story_json = story_json[7:-3]

            story_data = json.loads(story_json)
            return story_data
        except Exception as e:
            logging.error(f"Error getting story from Gemini: {e}")
            return self.get_fallback_story()

    def get_fallback_story(self):
        """Fallback story if API fails"""
        return random.choice(self.fallback_stories)

    def get_story(self):
        """Get a random story from a random category"""
        category = random.choice(self.story_categories)
        return self.get_story_from_gemini(category)
