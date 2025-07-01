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

        logging.info(f"Enabled platforms: {self.enabled_platforms}")

    def generate_and_upload_short(self):
        """Generate a single short and upload to all enabled platforms"""
        try:
            # Generate story
            story = self.story_generator.get_story()
            if not story:
                logging.error("Failed to generate story")
                return False

            # Create video
            video_path = self.video_creator.create_short_video(story)
            if not video_path:
                logging.error("Failed to create video")
                return False

            # Upload to all enabled platforms
            upload_results = {}
            for platform in self.enabled_platforms:
                if platform in self.uploaders:
                    try:
                        uploader = self.uploaders[platform]
                        success = uploader.upload(video_path, story)
                        upload_results[platform] = success

                        if success:
                            logging.info(f"Successfully uploaded to {platform}")
                        else:
                            logging.error(f"Failed to upload to {platform}")
                    except Exception as e:
                        logging.error(f"Error uploading to {platform}: {e}")
                        upload_results[platform] = False
                else:
                    logging.warning(f"Unknown platform: {platform}")

            # Clean up local file if at least one upload succeeded
            if any(upload_results.values()):
                try:
                    os.remove(video_path)
                    logging.info("Cleaned up local video file")
                except Exception as e:
                    logging.warning(f"Could not delete local file: {e}")

            success_count = sum(upload_results.values())
            total_count = len(upload_results)
            logging.info(f"Upload summary: {success_count}/{total_count} platforms successful")

            return success_count > 0

        except Exception as e:
            logging.error(f"Error in generate_and_upload_short: {e}")
            return False

    def refresh_token(self):
        if 'facebook' in self.enabled_platforms:
            logging.info("Refreshing Facebook access token...")
            self._refresh_facebook_token()

    def _refresh_facebook_token(self):
        access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        app_id = os.getenv("FACEBOOK_APP_ID")
        app_secret = os.getenv("FACEBOOK_APP_SECRET")

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
            data = response.json()
        except Exception as e:
            logging.error(f"Error during token refresh: {e}")
            return

        new_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 0))

        if not new_token:
            logging.error("No token returned from Facebook.")
            return

        expiry_datetime = datetime.now() + timedelta(seconds=expires_in)
        expiry_str = expiry_datetime.strftime("%Y-%m-%d %H:%M:%S")
        expiry_days = expires_in // 86400

        logging.info(f"New token received.")
        logging.info(f"Expires in: {expiry_days} days")
        logging.info(f"Expires on: {expiry_str}")

        self.update_env_token('FACEBOOK_ACCESS_TOKEN', new_token)

    def update_env_token(self, env_var, new_token):
        updated_lines = []
        token_pattern = re.compile(r'^\s*'+env_var+r'\s*=\s*.*$')
        replaced = False

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

    def run_daily_uploads(self):
        """Schedule and run token refresh"""
        logging.info("Starting token refresh automation...")
        schedule.every(55).days.at("03:00").do(self.refresh_token)
        logging.info(f"Scheduled token refresh every 55 days at 03:00 IST.")

        """Schedule and run daily uploads"""
        logging.info("Starting Multi-Platform Shorts automation...")

        # Schedule uploads based on environment variable
        upload_times = os.getenv('UPLOAD_TIMES', '00:00,04:00,08:00,12:00,16:00,20:00').split(',')
        tz_ist = pytz.timezone('Asia/Kolkata')

        for time_str in upload_times:
            time_str = time_str.strip()
            schedule.every().day.at(time_str, tz_ist).do(self.generate_and_upload_short)

        logging.info(f"Scheduled daily uploads at: {', '.join(upload_times)} IST.")

        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


if __name__ == "__main__":
    # Configuration
    logging.info("Loading environment variables from .env file...")
    load_dotenv(os.path.join(constants.CONFIG_DIR, '.env'))

    if os.getenv('FONT_PATH') is None:
        logging.error("Please set the FONT_PATH environment variable in your .env file.")
        sys.exit(1)

    bot = MultiPlatformShortsBot()

    # For testing - run once
    bot.refresh_token()
    bot.generate_and_upload_short()

    # For production - run scheduled uploads
    bot.run_daily_uploads()