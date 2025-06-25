import os
import pickle
import logging
from abc import ABC, abstractmethod
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from config import constants


class BaseUploader(ABC):
    """Abstract base class for platform uploaders"""

    @abstractmethod
    def upload(self, video_path, story):
        """Upload video to the platform"""
        pass

    @abstractmethod
    def get_platform_name(self):
        """Get the platform name"""
        pass


class YouTubeUploader(BaseUploader):
    def __init__(self):
        self.secrets_file = constants.CLIENT_SECRETS_FILE
        self.token_file = constants.YOUTUBE_TOKEN_FILE
        self.scopes = constants.SCOPES

        # Story categories for tags
        self.story_categories = [
            "Paranormal", "Supernatural", "Horror", "Psychological", "Mystery", "Creepy",
            "ScaryStory", "FoundFootage", "YouTubeShorts", "Shorts"
        ]

    def get_platform_name(self):
        return "YouTube"

    def get_authenticated_service(self):
        """Authenticates with YouTube and returns the service object."""
        creds = None

        # Load existing token
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token_file:
                    creds = pickle.load(token_file)
            except Exception as e:
                logging.error(f"Error loading YouTube token: {e}")
                try:
                    os.remove(self.token_file)
                except:
                    pass

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logging.error(f"Error refreshing YouTube token: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.secrets_file):
                    logging.error(f"YouTube credentials file not found: {self.secrets_file}")
                    return None

                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.secrets_file, self.scopes
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logging.error(f"YouTube authentication failed: {e}")
                    return None

            # Save credentials
            try:
                with open(self.token_file, 'wb') as token_file:
                    pickle.dump(creds, token_file)
                os.chmod(self.token_file, 0o600)
            except Exception as e:
                logging.warning(f"Could not save YouTube token: {e}")

        return build("youtube", "v3", credentials=creds)

    def upload(self, video_path, story):
        """Upload video to YouTube"""
        try:
            service = self.get_authenticated_service()
            if not service:
                return False

            title = f"Daily Dose of Short Stories #Shorts"
            description = f"""🔥 Daily Dose of Short Stories

✨ Follow for more stories
💪 Tag someone who needs this
🎯 Turn on notifications

#HorrorShort #YouTubeShorts #ScaryStory #Creepy #FoundFootage"""

            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': self.story_categories,
                    'categoryId': '22',
                    'defaultLanguage': 'en'
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
                }
            }

            media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
            request = service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logging.info(f"YouTube upload: {int(status.progress() * 100)}%")

            logging.info(f"YouTube upload complete! Video ID: {response['id']}")
            logging.info(f"Video URL: https://www.youtube.com/shorts/{response['id']}")
            return True

        except HttpError as e:
            logging.error(f"YouTube HTTP error {e.resp.status}: {e.content}")
            return False
        except Exception as e:
            logging.error(f"Error uploading to YouTube: {e}")
            return False


class FacebookUploader(BaseUploader):
    def __init__(self):
        self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        self.page_id = os.getenv('FACEBOOK_PAGE_ID')

    def get_platform_name(self):
        return "Facebook"

    def upload(self, video_path, story):
        """Upload video to Facebook"""
        try:
            if not self.access_token or not self.page_id:
                logging.error("Facebook credentials not configured")
                return False

            # TODO: Implement Facebook upload using Facebook Graph API
            # This would require the facebook-sdk library or direct HTTP requests

            logging.info("Facebook upload - Implementation needed")
            logging.info("Required: facebook-sdk library and Graph API integration")

            # Placeholder return
            return False

        except Exception as e:
            logging.error(f"Error uploading to Facebook: {e}")
            return False


class InstagramUploader(BaseUploader):
    def __init__(self):
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')

    def get_platform_name(self):
        return "Instagram"

    def upload(self, video_path, story):
        """Upload video to Instagram"""
        try:
            if not self.access_token or not self.account_id:
                logging.error("Instagram credentials not configured")
                return False

            # TODO: Implement Instagram upload using Instagram Basic Display API
            # This requires the video to be hosted publicly first

            logging.info("Instagram upload - Implementation needed")
            logging.info("Required: Instagram Basic Display API integration")

            # Placeholder return
            return False

        except Exception as e:
            logging.error(f"Error uploading to Instagram: {e}")
            return False