import json
import json
import logging
import os
import pickle
import random
import sys
import textwrap
import time
from datetime import datetime

import pytz
import schedule
from dotenv import load_dotenv
from google import genai
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from moviepy import VideoFileClip, TextClip, AudioFileClip, CompositeVideoClip
from moviepy import afx, vfx

from config import constants

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(levelname)s >>> %(message)s')

class YouTubeShortsBot:
    def __init__(self):
        # Configuration
        load_dotenv(os.path.join(constants.CONFIG_DIR, '.env'))

        self.gemini_api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
        self.youtube_secrets_file = constants.CLIENT_SECRETS_FILE
        self.youtube_token_file = constants.YOUTUBE_TOKEN_FILE
        self.scopes = constants.SCOPES
        self.redirect_uri = 'http://localhost/'
        self.fallback_stories = constants.FALLBACK_STORIES
        self.background_videos_folder = os.path.join(constants.ASSETS_DIR, 'background_videos')
        self.audios_folder = os.path.join(constants.ASSETS_DIR, 'audio_tracks')
        self.fonts_folder = constants.FONTS_DIR
        self.output_folder = os.path.join(constants.DATA_DIR, 'generated_shorts')

        # Ensure folders exist
        os.makedirs(self.background_videos_folder, exist_ok=True)
        os.makedirs(self.audios_folder, exist_ok=True)
        os.makedirs(self.fonts_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)

        # Story categories for variety
        self.story_categories = [
            "Paranormal/Supernatural", "Psychological Horror", "Creature Feature/Monster", "Home Invasion/Stalker",
            "Urban Legend/Folklore", "Techno-Horror", "Surprise/Twist Endings", "Dark Comedy/Absurdist",
            "Mystery (Micro-Mystery)", "Historical Horror"
        ]

    def get_story_from_gemini(self, category="Psychological Horror"):
        """Get a story from Google Gemini API"""
        client = genai.Client(api_key=self.gemini_api_key)

        prompt = f"""Generate an original, dank {category} story that would work well for a YouTube Short. 
                    The story should be:
                    - about 50 words maximum
                    - Easy to read on screen
                    - Not from any famous person (original)
                    - The story should have an immediate punch
            
                    Return the title and the story text as json with key 'title' and 'story' respectively, nothing else."""

        try:
            logging.info(f"Starting to fetch story from Gemini for category: {category}...")
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            story_json = response.text
            logging.info(f"Received response from Gemini: {story_json}")

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

    def create_video_short(self, story, background_video_path, audio_path, output_filename):
        """Create a video short with story overlay"""
        try:
            # Load background video
            background = VideoFileClip(background_video_path)

            # Resize to 9:16 aspect ratio (1080x1920 for YouTube Shorts)
            background = background.resized(height=1920)
            if background.w > 1080:
                background = background.cropped(x_center=background.w / 2, width=1080)

            # Limit duration to CLIP_DURATION seconds max for YouTube Shorts
            clip_duration = float(os.getenv('CLIP_DURATION', 20))  # Default to 20 seconds if not set
            if background.duration > clip_duration:
                background = background.with_duration(clip_duration)
            elif background.duration < clip_duration:
                # Loop background if shorter than CLIP_DURATION
                background = background.with_effects([vfx.Loop()]).with_duration(clip_duration)

            # Load audio track
            audio_clip = AudioFileClip(audio_path)
            if audio_clip.duration < background.duration:
                # Loop audio if shorter than video
                audio_clip = audio_clip.with_effects([afx.AudioLoop(duration=background.duration)])
            elif audio_clip.duration > background.duration:
                # Trim audio if longer than video
                audio_clip = audio_clip.with_duration(background.duration)

            # Wrap the text to a maximum width of 30 characters
            wrapped_text = textwrap.fill(story['story'], width=30)

            # Create text clip
            text_clip = TextClip(
                text=wrapped_text,
                font=os.path.join(self.fonts_folder, os.getenv('FONT_PATH')),
                color='white',
                stroke_color='black',
                stroke_width=3,
                method='caption',
                size=(900, 1920),
                font_size=70,
                text_align="center",
                interline=8,
                margin=(100, 50),
                duration=background.duration
            )

            # Compose final video
            logging.info(f"Starting shorts creation...")
            final_video = CompositeVideoClip([background, text_clip])

            # Export with optimized settings for YouTube
            output_path = os.path.join(self.output_folder, output_filename)
            final_video = final_video.with_audio(audio_clip)

            final_video.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio=True,
                audio_codec='aac',
                temp_audiofile=os.path.join(constants.DATA_DIR, 'temp-audio_tracks.m4a'),
                remove_temp=True,
                preset='medium',
                ffmpeg_params=['-crf', '23'],
                threads=8,
                logger=None
            )

            # Clean up
            background.close()
            audio_clip.close()
            final_video.close()

            logging.info(f"Video created successfully: {output_path}")
            return output_path

        except Exception as e:
            logging.error(f"Error creating video: {e}")
            return None

    def get_authenticated_service(self):
        """Authenticates with YouTube and returns the service object."""
        creds = None

        # Load existing token from pickle file
        if os.path.exists(self.youtube_token_file):
            try:
                with open(self.youtube_token_file, 'rb') as token_file:
                    creds = pickle.load(token_file)
                logging.info(f"Loaded credentials from {self.youtube_token_file}")
            except Exception as e:
                logging.error(f"Error loading token file: {e}")
                # Remove corrupted token file
                try:
                    os.remove(self.youtube_token_file)
                except:
                    pass

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logging.info("Refreshing expired token...")
                    creds.refresh(Request())
                    logging.info("Token refreshed successfully")
                except Exception as e:
                    logging.error(f"Error refreshing token: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.youtube_secrets_file):
                    logging.error(f"Credentials file not found: {self.youtube_secrets_file}")
                    return False

                # For headless systems, this will fail
                # You need to run this once on a system with a browser
                try:
                    logging.info("Starting OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.youtube_secrets_file, self.scopes
                    )
                    creds = flow.run_local_server(port=0)
                    logging.info("OAuth flow completed successfully")
                except Exception as e:
                    logging.error(f"Authentication failed: {e}")
                    logging.error("For headless systems:")
                    logging.error("1. Run this script once on a machine with a browser")
                    logging.error(f"2. Copy the generated {self.youtube_token_file} to your headless system")
                    return False

            # Save credentials using pickle
            try:
                with open(self.youtube_token_file, 'wb') as token_file:
                    pickle.dump(creds, token_file)
                logging.info(f"Credentials saved to {self.youtube_token_file}")

                # Set restrictive permissions on token file for security
                os.chmod(self.youtube_token_file, 0o600)
            except Exception as e:
                logging.warning(f"Warning: Could not save token file: {e}")

        return build("youtube", "v3", credentials=creds)


    def upload_to_youtube(self, video_path, title, description, tags):
        """Upload video to YouTube"""
        try:
            yt_svc = self.get_authenticated_service()

            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': '22',
                    'defaultLanguage': 'en'
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
                }
            }

            media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)

            request = yt_svc.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logging.info(f"Uploaded {int(status.progress() * 100)}%")

            logging.info(f"Upload Complete! Video ID: {response['id']}")
            logging.info(f"Video URL: https://www.youtube.com/shorts/{response['id']}")
            return True
        except HttpError as e:
            logging.error(f"An HTTP error {e.resp.status} occurred: {e.content}")
            return False
        except Exception as e:
            logging.error(f"Error uploading to YouTube: {e}")
            return False

    def get_story(self):
        # Get random category and story source
        category = random.choice(self.story_categories)
        story = self.get_story_from_gemini(category)
        return story

    def generate_short(self, story):
        """Generate a single short and upload it"""
        try:
            # Get random background video
            background_videos = [f for f in os.listdir(self.background_videos_folder)
                                 if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]

            if not background_videos:
                logging.error("No background videos found! Please add videos to the background_videos folder.")
                return False

            background_video = random.choice(background_videos)
            background_path = os.path.join(self.background_videos_folder, background_video)

            # Get random audio track
            audio_tracks = [f for f in os.listdir(self.audios_folder)
                            if f.lower().endswith(('.mp3', '.wav', '.aac'))]
            if not audio_tracks:
                logging.error("No audio tracks found! Please add audio files to the audio_tracks folder.")
                return False

            audio_track = random.choice(audio_tracks)
            audio_path = os.path.join(self.audios_folder, audio_track)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"short_{timestamp}.mp4"

            # Create video
            video_path = self.create_video_short(story, background_path, audio_path, output_filename)
            if not video_path:
                return False

            return video_path
        except Exception as e:
            logging.error(f"Error in generate_short: {e}")
            return None

    def generate_and_upload_short(self):
        """Generate a single short and upload it"""
        try:
            story = self.get_story()

            # Generate a short video
            video_path = self.generate_short(story)
            # Upload to YouTube
            title = f"Daily Dose of Short Stories #Shorts"
            description = f"""🔥 Daily Dose of Short Stories
                                        
                            ✨ Follow for more stories
                            💪 Tag someone who needs this
                            🎯 Turn on notifications
                            
                            #HorrorShort #YouTubeShorts #ScaryStory #Creepy #FoundFootage"""

            tags = self.story_categories

            success = self.upload_to_youtube(video_path, title, description, tags)

            if success:
                logging.info(f"Successfully created and uploaded video")
                # Delete the local file to save space
                os.remove(video_path)

            return success
        except Exception as e:
            logging.error(f"Error in generate_and_upload_short: {e}")
            return False

    def run_daily_uploads(self):
        """Schedule and run daily uploads"""
        logging.info("Starting YouTube Shorts automation...")

        # Schedule 6 uploads per day
        tz_ist = pytz.timezone('Asia/Kolkata')

        schedule.every().day.at("00:00", tz_ist).do(self.generate_and_upload_short)
        schedule.every().day.at("04:00", tz_ist).do(self.generate_and_upload_short)
        schedule.every().day.at("08:00", tz_ist).do(self.generate_and_upload_short)
        schedule.every().day.at("12:00", tz_ist).do(self.generate_and_upload_short)
        schedule.every().day.at("16:00", tz_ist).do(self.generate_and_upload_short)
        schedule.every().day.at("20:00", tz_ist).do(self.generate_and_upload_short)

        logging.info(f"Scheduled daily uploads at 00:00, 04:00, 08:00, 12:00, 16:00, and 20:00 IST.")

        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


# Usage example
if __name__ == "__main__":
    bot = YouTubeShortsBot()

    bot.generate_and_upload_short()

    if os.getenv('FONT_PATH') is None:
        logging.error("Please set the FONT_PATH environment variable in your .env file.")
        sys.exit(1)

    # For production - run scheduled uploads
    bot.run_daily_uploads()
