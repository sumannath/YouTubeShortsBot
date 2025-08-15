import os
import pickle
import logging
import requests
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
            summary = story['summary'] if 'summary' in story else 'A chilling tale of the unknown.'
            description = f"""🔥 Daily Dose of Stories
            
{summary}

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
        self.api_version = "v23.0"
        self.video_url = "https://graph-video.facebook.com"
        self.base_url = "https://graph.facebook.com"
        self.page_access_token = None
        self.file_path = None

    def get_platform_name(self):
        return "Facebook"

    def _get_page_access_token(self):
        """Get a page-specific access token from the user access token"""
        try:
            if self.page_access_token:
                return self.page_access_token

            url = f"{self.base_url}/{self.api_version}/me/accounts"
            params = {'access_token': self.access_token}
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            for page in data.get('data', []):
                if page['id'] == self.page_id:
                    self.page_access_token = page['access_token']
                    logging.info(f"Found page access token for page {self.page_id}")
                    return self.page_access_token

            logging.error(f"Could not find page access token for page ID {self.page_id}")
            return None

        except Exception as e:
            logging.error(f"Error getting page access token: {e}")
            return None

    def _initiate_resumable_upload(self):
        url = f"{self.video_url}/{self.api_version}/{self.page_id}/videos"
        params = {
            'upload_phase': 'start',
            'file_size': os.path.getsize(self.file_path),
            'access_token': self.page_access_token
        }
        response = requests.post(url, data=params)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Upload session started: {data}")
        return data['upload_session_id'], data['video_id'], data['start_offset'], data['end_offset']

    def _upload_chunks(self, upload_session_id, start_offset, end_offset):
        with open(self.file_path, 'rb') as f:
            while True:
                f.seek(int(start_offset))
                chunk = f.read(int(end_offset) - int(start_offset))

                url = f"{self.video_url}/{self.api_version}/{self.page_id}/videos"
                files = {
                    'video_file_chunk': ('chunk', chunk)
                }
                params = {
                    'upload_phase': 'transfer',
                    'upload_session_id': upload_session_id,
                    'start_offset': start_offset,
                    'access_token': self.page_access_token
                }

                response = requests.post(url, data=params, files=files)
                response.raise_for_status()
                data = response.json()
                logging.info(f"Uploaded chunk: start={start_offset}, end={end_offset}")

                if data['start_offset'] == data['end_offset']:
                    break

                start_offset = data['start_offset']
                end_offset = data['end_offset']

    def _finish_upload(self, upload_session_id, title, description):
        url = f"{self.video_url}/{self.api_version}/{self.page_id}/videos"
        params = {
            'upload_phase': 'finish',
            'upload_session_id': upload_session_id,
            'title': title,
            'description': description,
            'access_token': self.page_access_token,
            'is_reel': 'true'
        }

        response = requests.post(url, data=params)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Upload finished. Response: {data}")
        return data.get("success", False)

    def upload(self, video_path, story=None):
        """Main upload method"""
        self.file_path = video_path
        try:
            if not self.access_token or not self.page_id:
                logging.error("Missing Facebook credentials.")
                return False

            if not os.path.exists(video_path):
                logging.error(f"Video file not found: {video_path}")
                return False

            logging.info("Retrieving page access token...")
            if not self._get_page_access_token():
                return False

            logging.info("Starting upload session...")
            upload_session_id, video_id, start_offset, end_offset = self._initiate_resumable_upload()

            logging.info("Uploading video chunks...")
            self._upload_chunks(upload_session_id, start_offset, end_offset)

            logging.info("Finalizing video upload...")
            title = "Daily Dose of Short Stories"
            description = f"""🔥 Daily Dose of Short Stories

✨ Follow for more stories
💪 Tag someone who needs this
🎯 Turn on notifications

#HorrorShort #ScaryStory #Creepy #ShortVideo"""
            success = self._finish_upload(upload_session_id, title, description)

            if success:
                logging.info(f"Video uploaded successfully: https://www.facebook.com/watch/?v={video_id}")
                return True
            else:
                logging.error("Failed to finish Facebook video upload.")
                return False

        except requests.RequestException as e:
            logging.error(f"RequestException during Facebook upload: {e}")
            if e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error uploading to Facebook: {e}")
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