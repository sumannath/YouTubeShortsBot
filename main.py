import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta

import pytz
import requests
import schedule
from dotenv import load_dotenv

from config import constants
from platform_uploaders import YouTubeUploader, FacebookUploader, InstagramUploader
from story_generator import StoryGenerator
from video_creator import VideoCreator

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(levelname)s >>> %(message)s')


class MultiPlatformShortsBot:
    def __init__(self):
        # Initialize components
        self.dot_env_file = os.path.join(constants.CONFIG_DIR, '.env')
        self.story_generator = StoryGenerator()
        self.video_creator = VideoCreator()
        self.uploaders = {
            'youtube': YouTubeUploader(),
            'facebook': FacebookUploader(),
            'instagram': InstagramUploader()
        }

        # Get enabled platforms from environment
        self.enabled_platforms = os.getenv('ENABLED_PLATFORMS', 'youtube').split(',')
        self.enabled_platforms = [platform.strip().lower() for platform in self.enabled_platforms]

        # Video type configuration
        self.video_types = os.getenv('VIDEO_TYPES', 'short').split(',')
        self.video_types = [vtype.strip().lower() for vtype in self.video_types]

        logging.info(f"Enabled platforms: {self.enabled_platforms}")

    def generate_and_upload_short(self):
        """Generate a short video and upload to all enabled platforms"""
        try:
            # Generate short story
            story = self.story_generator.get_story(story_type="short")
            if not story:
                logging.error("Failed to generate short story")
                return False

            # Create short video
            video_path = self.video_creator.create_short_video(story)
            if not video_path:
                logging.error("Failed to create short video")
                return False

            # Upload to all enabled platforms
            return self._upload_to_platforms(video_path, story, "short")

        except Exception as e:
            logging.error(f"Error in generate_and_upload_short: {e}")
            return False

    def generate_and_upload_long(self):
        """Generate a long video and upload to all enabled platforms"""
        try:
            # Generate long story
            story = self.story_generator.get_story(story_type="long")
            if not story:
                logging.error("Failed to generate long story")
                return False

            # Create long video
            video_path = self.video_creator.create_long_story_video(story)
            if not video_path:
                logging.error("Failed to create long video")
                return False

            # Upload to all enabled platforms
            return self._upload_to_platforms(video_path, story, "long")

        except Exception as e:
            logging.error(f"Error in generate_and_upload_long: {e}")
            return False

    def _upload_to_platforms(self, video_path, story, video_type):
        """Upload video to all enabled platforms"""
        upload_results = {}
        for platform in self.enabled_platforms:
            if platform in self.uploaders:
                try:
                    uploader = self.uploaders[platform]

                    # Pass video type to uploader for custom handling
                    if hasattr(uploader, 'set_video_type'):
                        uploader.set_video_type(video_type)

                    success = uploader.upload(video_path, story)
                    upload_results[platform] = success

                    if success:
                        logging.info(f"Successfully uploaded {video_type} video to {platform}")
                    else:
                        logging.error(f"Failed to upload {video_type} video to {platform}")
                except Exception as e:
                    logging.error(f"Error uploading {video_type} video to {platform}: {e}")
                    upload_results[platform] = False
            else:
                logging.warning(f"Unknown platform: {platform}")

        # Clean up local file if at least one upload succeeded
        if any(upload_results.values()):
            try:
                os.remove(video_path)
                logging.info(f"Cleaned up local {video_type} video file")
            except Exception as e:
                logging.warning(f"Could not delete local file: {e}")

        success_count = sum(upload_results.values())
        total_count = len(upload_results)
        logging.info(
            f"{video_type.capitalize()} video upload summary: {success_count}/{total_count} platforms successful")

        return success_count > 0

    def generate_mixed_content(self):
        """Generate either short or long content based on configuration"""
        if 'short' in self.video_types and 'long' in self.video_types:
            # Randomly choose between short and long
            import random
            video_type = random.choice(['short', 'long'])
        elif 'long' in self.video_types:
            video_type = 'long'
        else:
            video_type = 'short'

        if video_type == 'long':
            return self.generate_and_upload_long()
        else:
            return self.generate_and_upload_short()

    def refresh_token(self):
        """Refresh Facebook access token if Facebook is enabled"""
        if 'facebook' in self.enabled_platforms:
            logging.info("Refreshing Facebook access token...")
            self._refresh_facebook_token()

    def _refresh_facebook_token(self):
        """Internal method to refresh Facebook access token"""
        access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        app_id = os.getenv("FACEBOOK_APP_ID")
        app_secret = os.getenv("FACEBOOK_APP_SECRET")

        if not all([access_token, app_id, app_secret]):
            logging.error("Missing Facebook credentials in environment variables")
            return

        url = "https://graph.facebook.com/v23.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": access_token
        }

        logging.info("Requesting new access token...")
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP error during token refresh: {e}")
            return
        except ValueError as e:
            logging.error(f"JSON decode error during token refresh: {e}")
            return
        except Exception as e:
            logging.error(f"Unexpected error during token refresh: {e}")
            return

        new_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 0))

        if not new_token:
            logging.error("No token returned from Facebook.")
            logging.error(f"Response: {data}")
            return

        expiry_datetime = datetime.now() + timedelta(seconds=expires_in)
        expiry_str = expiry_datetime.strftime("%Y-%m-%d %H:%M:%S")
        expiry_days = expires_in // 86400

        logging.info(f"New token received.")
        logging.info(f"Expires in: {expiry_days} days")
        logging.info(f"Expires on: {expiry_str}")

        self.update_env_token('FACEBOOK_ACCESS_TOKEN', new_token)

    def update_env_token(self, env_var, new_token):
        """Update environment variable in .env file"""
        if not os.path.exists(self.dot_env_file):
            logging.error(f".env file not found: {self.dot_env_file}")
            return

        updated_lines = []
        token_pattern = re.compile(r'^\s*' + re.escape(env_var) + r'\s*=\s*.*$')
        replaced = False

        try:
            with open(self.dot_env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                if token_pattern.match(line):
                    updated_lines.append(f"{env_var}={new_token}\n")
                    replaced = True
                else:
                    updated_lines.append(line)

            if not replaced:
                updated_lines.append(f"\n{env_var}={new_token}\n")

            with open(self.dot_env_file, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)

            os.environ[env_var] = new_token
            logging.info(".env updated successfully!")

        except Exception as e:
            logging.error(f"Error updating .env file: {e}")

    def run_daily_uploads(self):
        """Schedule and run daily uploads and token refresh"""
        logging.info("Starting Multi-Platform Shorts automation...")

        # Schedule token refresh
        logging.info("Setting up token refresh automation...")
        schedule.every(55).days.at("03:00").do(self.refresh_token)
        logging.info("Scheduled token refresh every 55 days at 03:00 IST.")

        # Schedule uploads based on environment variable
        upload_times = os.getenv('UPLOAD_TIMES', '00:00,04:00,08:00,12:00,16:00,20:00').split(',')
        tz_ist = pytz.timezone('Asia/Kolkata')

        for time_str in upload_times:
            time_str = time_str.strip()
            try:
                # Validate time format
                datetime.strptime(time_str, '%H:%M')
                schedule.every().day.at(time_str, tz_ist).do(self.generate_and_upload_short)
            except ValueError:
                logging.warning(f"Invalid time format: {time_str}. Expected HH:MM format.")
                continue

        logging.info(f"Scheduled daily uploads at: {', '.join(upload_times)} IST.")

        # Main loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logging.info("Received keyboard interrupt. Shutting down...")
                break
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(60)  # Continue after error


if __name__ == "__main__":
    # Configuration
    logging.info("Loading environment variables from .env file...")

    # Load environment variables
    env_path = os.path.join(constants.CONFIG_DIR, '.env')
    if not os.path.exists(env_path):
        logging.error(f".env file not found at {env_path}")
        sys.exit(1)

    load_dotenv(env_path)

    # Check required environment variables
    if os.getenv('FONT_PATH') is None:
        logging.error("Please set the FONT_PATH environment variable in your .env file.")
        sys.exit(1)

    try:
        bot = MultiPlatformShortsBot()

        # For testing - run once
        logging.info("Running initial token refresh...")
        bot.refresh_token()

        logging.info("Running test upload...")
        bot.generate_and_upload_long()

        # For production - run scheduled uploads
        logging.info("Starting scheduled uploads...")
        bot.run_daily_uploads()

    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)