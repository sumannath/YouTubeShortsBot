import os
import random
import time
from datetime import datetime

import schedule
from dotenv import load_dotenv
from google import genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy import VideoFileClip, TextClip, CompositeVideoClip


class YouTubeShortsBot:
    def __init__(self):
        # Configuration
        load_dotenv()
        self.gemini_api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
        self.youtube_credentials_file = "youtube_credentials.json"
        self.background_videos_folder = "background_videos"
        self.output_folder = "generated_shorts"

        # Ensure folders exist
        os.makedirs(self.background_videos_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)

        # Quote categories for variety
        self.quote_categories = [
            "motivation", "success", "life wisdom", "happiness",
            "perseverance", "growth mindset", "inspiration", "mindfulness"
        ]

    def get_quote_from_gemini(self, category="motivation"):
        """Get a quote from Google Gemini API"""
        client = genai.Client(api_key=self.gemini_api_key)

        prompt = f"""Generate an original, inspiring {category} quote that would work well for a YouTube Short. 
        The quote should be:
        - about 25 words maximum
        - Motivational and positive
        - Easy to read on screen
        - Not from any famous person (original)

        Return only the quote text, nothing else."""

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            quote = response.text
            quote = quote.replace('"', '').replace("'", "")
            print(f"Generated quote from Gemini: {quote}")
            return quote
        except Exception as e:
            print(f"Error getting quote from Gemini: {e}")
            return self.get_fallback_quote()

    def get_fallback_quote(self):
        """Fallback quotes if API fails"""
        fallback_quotes = [
            "Success doesn’t come overnight. Stay consistent, stay patient. Small steps every day create momentum that leads to massive, life-changing results.",
            "Your journey is yours alone. Don’t compare. Keep showing up, even when it’s hard. That’s how strength and greatness are built.",
            "The only limit is the one you place on yourself. Believe bigger, act bolder, and watch your life transform beyond imagination.",
            "Discipline beats motivation. Show up on the days you don’t feel like it—those are the days that shape your future the most.",
            "Fear is normal. Let it walk beside you, not control you. Courage is action in the presence of fear, not the absence of it.",
            "Don’t wait for the perfect time—it doesn’t exist. Start now, with what you have. Progress loves action, not perfection.",
            "Your comfort zone is beautiful, but nothing ever grows there. Step out. That’s where the magic of growth, change, and strength begins.",
            "You’re stronger than you think. Every setback is a setup for a comeback. Keep going—you haven’t come this far just to stop now.",
            "Greatness isn’t born; it’s earned with sweat, late nights, and persistence. Keep grinding. The effort will echo in your success story.",
            "Each day is a fresh page. Write boldly. Mistakes don’t define you—how you rise after them does. Keep rewriting your story with strength."
        ]
        return random.choice(fallback_quotes)

    def create_video_short(self, quote_text, background_video_path, output_filename):
        """Create a video short with quote overlay"""
        try:
            # Load background video
            background = VideoFileClip(background_video_path)

            # Resize to 9:16 aspect ratio (1080x1920 for YouTube Shorts)
            background = background.resized(height=1920)
            if background.w > 1080:
                background = background.cropped(x_center=background.w / 2, width=1080)

            # Limit duration to 60 seconds max for YouTube Shorts
            if background.duration > 60:
                background = background.subclip(0, 60)

            # Create text clip
            text_clip = TextClip(
                text=quote_text,
                font=None,
                font_size=70,
                color='white',
                stroke_color='black',
                stroke_width=3,
                method='caption',
                size=(900, None),
                text_align="center",
                duration=background.duration
            )

            # Compose final video
            final_video = CompositeVideoClip([background, text_clip])

            # Export with optimized settings for YouTube
            output_path = os.path.join(self.output_folder, output_filename)
            final_video.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                preset='medium',
                ffmpeg_params=['-crf', '23']
            )

            # Clean up
            background.close()
            final_video.close()

            return output_path

        except Exception as e:
            print(f"Error creating video: {e}")
            return None

    def upload_to_youtube(self, video_path, title, description, tags):
        """Upload video to YouTube"""
        try:
            # Load YouTube API credentials
            credentials = Credentials.from_authorized_user_file(self.youtube_credentials_file)
            youtube = build('youtube', 'v3', credentials=credentials)

            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': '22',  # People & Blogs
                    'defaultLanguage': 'en'
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
                }
            }

            media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)

            request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = request.execute()
            print(f"Video uploaded successfully: https://youtube.com/watch?v={response['id']}")
            return True

        except Exception as e:
            print(f"Error uploading to YouTube: {e}")
            return False

    def generate_and_upload_short(self):
        """Generate a single short and upload it"""
        try:
            # Get random category and quote source
            category = random.choice(self.quote_categories)

            quote = self.get_quote_from_gemini(category)

            # Get random background video
            background_videos = [f for f in os.listdir(self.background_videos_folder)
                                 if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]

            if not background_videos:
                print("No background videos found! Please add videos to the background_videos folder.")
                return False

            background_video = random.choice(background_videos)
            background_path = os.path.join(self.background_videos_folder, background_video)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"short_{timestamp}.mp4"

            # Create video
            video_path = self.create_video_short(quote, background_path, output_filename)
            if not video_path:
                return False

            # Upload to YouTube
            title = f"Daily Motivation #{timestamp[:8]} #Shorts"
            description = f"""🔥 Daily Motivation Quote

"{quote}"

✨ Follow for daily inspiration
💪 Tag someone who needs this
🎯 Turn on notifications

#motivation #inspiration #quotes #mindset #success #shorts #dailymotivation #motivationalquotes"""

            tags = ['motivation', 'inspiration', 'quotes', 'shorts', 'success', 'mindset', 'daily', 'motivational']

            # success = self.upload_to_youtube(video_path, title, description, tags)
            #
            # if success:
            #     print(f"Successfully created and uploaded: {output_filename}")
            #     # Optionally delete the local file to save space
            #     # os.remove(video_path)
            #
            # return success

        except Exception as e:
            print(f"Error in generate_and_upload_short: {e}")
            return False

    def run_daily_uploads(self):
        """Schedule and run daily uploads"""
        print("Starting YouTube Shorts automation...")

        # Schedule 2 uploads per day
        schedule.every().day.at("09:00").do(self.generate_and_upload_short)
        schedule.every().day.at("18:00").do(self.generate_and_upload_short)

        print("Scheduled uploads at 9:00 AM and 6:00 PM daily")

        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


# Usage example
if __name__ == "__main__":
    bot = YouTubeShortsBot()

    # For testing - generate one short immediately
    bot.generate_and_upload_short()

    # For production - run scheduled uploads
    bot.run_daily_uploads()
