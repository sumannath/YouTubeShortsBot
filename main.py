import itertools
import os
import pickle
import random
import sys
import textwrap
import threading
import time
from datetime import datetime

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


class YouTubeShortsBot:
    def __init__(self):
        # Configuration
        load_dotenv(os.path.join(constants.CONFIG_DIR, '.env'))

        self.gemini_api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
        self.youtube_secrets_file = constants.CLIENT_SECRETS_FILE
        self.youtube_token_file = constants.YOUTUBE_TOKEN_FILE
        self.scopes = constants.SCOPES
        self.redirect_uri = 'http://localhost/'
        self.fallback_quotes = constants.FALLBACK_QUOTES
        self.background_videos_folder = os.path.join(constants.ASSETS_DIR, 'background_videos')
        self.audios_folder = os.path.join(constants.ASSETS_DIR, 'audio_tracks')
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
        - about 50 words maximum
        - Motivational and positive
        - Easy to read on screen
        - Not from any famous person (original)
        - The quote should have an immediate punch

        Return only the quote text, nothing else."""

        stop_event = threading.Event()

        def loader():
            spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
            sys.stdout.write("Generating quote from Gemini... ")
            while not stop_event.is_set():
                sys.stdout.write(next(spinner))
                sys.stdout.flush()
                time.sleep(0.1)
                sys.stdout.write('\b')
            sys.stdout.write("Done!\n")

        try:
            t = threading.Thread(target=loader)
            t.start()

            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )

            stop_event.set()
            t.join()

            quote = response.text
            quote = quote.replace('"', '').replace("'", "")
            print(f"Generated quote from Gemini: {quote}")
            return quote
        except Exception as e:
            print(f"Error getting quote from Gemini: {e}")
            stop_event.set()
            return self.get_fallback_quote()

    def get_fallback_quote(self):
        """Fallback quotes if API fails"""
        return random.choice(self.fallback_quotes)

    def create_video_short(self, quote_text, background_video_path, audio_path, output_filename):
        """Create a video short with quote overlay"""
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
            wrapped_text = textwrap.fill(quote_text, width=30)

            # Create text clip
            text_clip = TextClip(
                text=wrapped_text,
                font=os.path.join(constants.FONTS_DIR, os.getenv('FONT_PATH')),
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
                threads=8
            )

            # Clean up
            background.close()
            audio_clip.close()
            final_video.close()

            return output_path

        except Exception as e:
            print(f"Error creating video: {e}")
            return None

    def get_authenticated_service(self):
        """Authenticates with YouTube and returns the service object."""
        creds = None

        # Load existing token from pickle file
        if os.path.exists(self.youtube_token_file):
            try:
                with open(self.youtube_token_file, 'rb') as token_file:
                    creds = pickle.load(token_file)
                print(f"Loaded credentials from {self.youtube_token_file}")
            except Exception as e:
                print(f"Error loading token file: {e}")
                # Remove corrupted token file
                try:
                    os.remove(self.youtube_token_file)
                except:
                    pass

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("Refreshing expired token...")
                    creds.refresh(Request())
                    print("Token refreshed successfully")
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.youtube_secrets_file):
                    print(f"Credentials file not found: {self.youtube_secrets_file}")
                    return False

                # For headless systems, this will fail
                # You need to run this once on a system with a browser
                try:
                    print("Starting OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.youtube_secrets_file, self.scopes
                    )
                    creds = flow.run_local_server(port=0)
                    print("OAuth flow completed successfully")
                except Exception as e:
                    print(f"Authentication failed: {e}")
                    print("For headless systems:")
                    print("1. Run this script once on a machine with a browser")
                    print(f"2. Copy the generated {self.youtube_token_file} to your headless system")
                    return False

            # Save credentials using pickle
            try:
                with open(self.youtube_token_file, 'wb') as token_file:
                    pickle.dump(creds, token_file)
                print(f"Credentials saved to {self.youtube_token_file}")

                # Set restrictive permissions on token file for security
                os.chmod(self.youtube_token_file, 0o600)
            except Exception as e:
                print(f"Warning: Could not save token file: {e}")

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
                    print(f"Uploaded {int(status.progress() * 100)}%")

            print(f"Upload Complete! Video ID: {response['id']}")
            print(f"Video URL: https://www.youtube.com/watch?v={response['id']}")
            return True
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred: {e.content}")
        except Exception as e:
            print(f"Error uploading to YouTube: {e}")
            return False

    def generate_and_upload_short(self):
        """Generate a single short and upload it"""
        try:
            # Get random category and quote source
            category = random.choice(self.quote_categories)

            quote = self.get_quote_from_gemini(category)
            # quote = self.get_fallback_quote()  # For testing, use fallback quote

            # Get random background video
            background_videos = [f for f in os.listdir(self.background_videos_folder)
                                 if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]

            if not background_videos:
                print("No background videos found! Please add videos to the background_videos folder.")
                return False

            background_video = random.choice(background_videos)
            background_path = os.path.join(self.background_videos_folder, background_video)

            # Get random audio track
            audio_tracks = [f for f in os.listdir(self.audios_folder)
                            if f.lower().endswith(('.mp3', '.wav', '.aac'))]
            if not audio_tracks:
                print("No audio tracks found! Please add audio files to the audio_tracks folder.")
                return False

            audio_track = random.choice(audio_tracks)
            audio_path = os.path.join(self.audios_folder, audio_track)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"short_{timestamp}.mp4"

            # Create video
            video_path = self.create_video_short(quote, background_path, audio_path, output_filename)
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

            success = self.upload_to_youtube(video_path, title, description, tags)

            if success:
                print(f"Successfully created and uploaded: {output_filename}")
                # Optionally delete the local file to save space
                # os.remove(video_path)

            return success
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

    if os.getenv('FONT_PATH') is None:
        print("Please set the FONT_PATH environment variable in your .env file.")
        sys.exit(1)

    # For testing - generate one short immediately
    bot.generate_and_upload_short()

    # For production - run scheduled uploads
    # bot.run_daily_uploads()
