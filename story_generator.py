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
        self.fallback_long_stories = constants.FALLBACK_LONG_STORIES if hasattr(constants,
                                                                                'FALLBACK_LONG_STORIES') else []

        # Story categories for variety
        self.story_categories = [
            "Paranormal/Supernatural", "Psychological Horror", "Creature Feature/Monster",
            "Home Invasion/Stalker", "Urban Legend/Folklore", "Techno-Horror",
            "Surprise/Twist Endings", "Dark Comedy/Absurdist", "Mystery (Micro-Mystery)",
            "Historical Horror"
        ]

        # Extended categories for longer stories
        self.long_story_categories = [
            "Paranormal Investigation", "Psychological Thriller", "Supernatural Mystery",
            "Urban Legend Deep Dive", "Horror Adventure", "Haunted Location",
            "Time Loop Horror", "Possession Story", "Cult Mystery", "Apocalyptic Horror",
            "Body Horror", "Cosmic Horror", "Folk Horror", "Gothic Horror"
        ]

    def get_story_from_gemini(self, category="Psychological Horror"):
        """Get a short story from Google Gemini API"""
        if not self.gemini_api_key:
            logging.warning("No Gemini API key found, using fallback story")
            return self.get_fallback_story()

        client = genai.Client(api_key=self.gemini_api_key)

        prompt = f"""Generate an original, simple but interesting {category} story that would work well for a YouTube Short. 
                    The story should be:
                    - about 50 words maximum
                    - Easy to read on screen
                    - Not from any famous person (original)
                    - The story should have an immediate punch
                    - Focus on a single, unsettling image or sound
                    - should leave on a cliffhanger and for users to think what happens next 

                    Return the title and the story text as json with key 'title' and 'story' respectively, nothing else."""

        try:
            logging.info(f"Fetching short story from Gemini for category: {category}...")
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

    def get_long_story_from_gemini(self, category="Psychological Thriller"):
        """Get a longer story from Google Gemini API for 5-minute videos"""
        if not self.gemini_api_key:
            logging.warning("No Gemini API key found, using fallback long story")
            return self.get_fallback_long_story()

        client = genai.Client(api_key=self.gemini_api_key)

        prompt = f"""Generate an original, engaging {category} story that would work well for a 5-minute YouTube video. 
                    The story should be:
                    - 600-800 words (approximately 4-5 minutes when read aloud)
                    - Engaging and atmospheric with vivid descriptions
                    - Have a clear beginning, middle, and end
                    - Include dialogue and character development
                    - Build tension throughout
                    - Have a satisfying but potentially open-ended conclusion
                    - Be suitable for audio narration
                    - Original content, not based on existing works
                    - Include sensory details (sounds, sights, feelings)
                    - Use short to medium paragraphs for better pacing

                    The story should be structured with:
                    - Hook opening that immediately draws listeners in
                    - Character introduction and setting establishment
                    - Rising tension and conflict
                    - Climax or revelation
                    - Resolution that may leave room for interpretation

                    Return the title, the story text and a short summary as json with key 'title', 'story' and 'summary' respectively, nothing else."""

        try:
            logging.info(f"Fetching long story from Gemini for category: {category}...")
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            story_json = response.text
            logging.info(f"Received long story response from Gemini")

            if story_json.startswith('```json'):
                story_json = story_json[7:-3]

            story_data = json.loads(story_json)

            # Validate story length (rough estimate)
            word_count = len(story_data['story'].split())
            if word_count < 400:
                logging.warning(f"Story seems short ({word_count} words), requesting extension...")
                return self._extend_story(story_data, category)

            return story_data
        except Exception as e:
            logging.error(f"Error getting long story from Gemini: {e}")
            return self.get_fallback_long_story()

    def _extend_story(self, story_data, category):
        """Extend a story that's too short"""
        try:
            client = genai.Client(api_key=self.gemini_api_key)

            extend_prompt = f"""The following {category} story needs to be extended to 600-800 words for a 5-minute video:

Title: {story_data['title']}
Story: {story_data['story']}

Please extend this story by:
- Adding more atmospheric details and sensory descriptions
- Developing the characters more fully
- Expanding the tension and suspense
- Adding more dialogue if appropriate
- Deepening the emotional impact
- Ensuring the pacing works well for audio narration

Return the extended story as json with key 'title' and 'story' respectively, nothing else."""

            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=extend_prompt
            )
            extended_json = response.text

            if extended_json.startswith('```json'):
                extended_json = extended_json[7:-3]

            return json.loads(extended_json)
        except Exception as e:
            logging.error(f"Error extending story: {e}")
            return story_data  # Return original if extension fails

    def get_fallback_story(self):
        """Fallback short story if API fails"""
        return random.choice(self.fallback_stories)

    def get_fallback_long_story(self):
        """Fallback long story if API fails"""
        if not self.fallback_long_stories:
            # Create a basic long story if none exist
            return {
                "title": "The Last Signal",
                "story": """The radio crackled to life at 3:33 AM, the static cutting through the silence of the abandoned research station. Dr. Sarah Chen had been alone here for three weeks, monitoring the deep space communication array, waiting for any sign of the lost expedition.

The voice that emerged from the speakers was barely human, distorted by distance and interference. "This is Commander Morrison... if anyone can hear this... we found something out here."

Sarah's hands trembled as she adjusted the frequency. The expedition had been missing for six months, their last known position somewhere in the outer rim of the solar system. Everyone assumed they were dead.

"The structure... it's not natural. It's calling to us, pulling us in. We can't resist it anymore. The crew... they're changing. I can feel it happening to me too."

The transmission cut to static, then resumed with a different voice – younger, more desperate. "This is Lieutenant Park. Don't come looking for us. Whatever you do, don't follow our trajectory. It's waiting for more of us. It's been waiting for so long."

Sarah checked the signal source. According to her instruments, the transmission was coming from Earth's moon. But that was impossible – the expedition had been heading toward Jupiter.

The radio sparked again, and this time, the voice was her own. "Dr. Chen, you need to leave the station now. You've been there too long. Can you feel it? The pull? We're coming home, Sarah. All of us."

Outside her window, Sarah saw lights moving across the lunar surface – lights that shouldn't exist. The radio continued to broadcast her own voice, speaking words she had never said, describing things she had never seen.

But somehow, she remembered them all."""
            }
        return random.choice(self.fallback_long_stories)

    def get_story(self, story_type="short"):
        """Get a story based on type (short or long)"""
        if story_type == "long":
            category = random.choice(self.long_story_categories)
            return self.get_long_story_from_gemini(category)
        else:
            category = random.choice(self.story_categories)
            return self.get_story_from_gemini(category)

    def get_long_story(self):
        """Get a long story for 5-minute videos"""
        return self.get_story(story_type="long")