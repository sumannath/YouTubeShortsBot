import logging
import os
import random
import textwrap
import warnings
from datetime import datetime

from google.cloud import texttospeech, storage
from moviepy import VideoFileClip, TextClip, AudioFileClip, CompositeVideoClip
from moviepy import afx, vfx
from tenacity import sleep

from config import constants
from ffmpeg_video_creator import FFMPEGVideoCreator

warnings.filterwarnings("ignore")

class VideoCreator:
    def __init__(self):
        self.background_videos_folder = os.path.join(constants.ASSETS_DIR, 'background_videos')
        self.audios_folder = os.path.join(constants.ASSETS_DIR, 'audio_tracks')
        self.fonts_folder = constants.FONTS_DIR
        self.output_folder = os.path.join(constants.DATA_DIR, 'generated_shorts')
        self.long_output_folder = os.path.join(constants.DATA_DIR, 'generated_long_videos')

        # Ensure folders exist
        os.makedirs(self.background_videos_folder, exist_ok=True)
        os.makedirs(self.audios_folder, exist_ok=True)
        os.makedirs(self.fonts_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.long_output_folder, exist_ok=True)

        # Azure TTS configuration
        self.azure_endpoint = os.getenv('AZURE_SPEECH_ENDPOINT')
        self.azure_key = os.getenv('AZURE_SPEECH_KEY')
        self.azure_region = os.getenv('AZURE_SPEECH_REGION', 'eastus')
        self.azure_voice = os.getenv('AZURE_VOICE_NAME', 'en-US-JennyNeural')

    def get_random_background_video(self):
        """Get a random background video"""
        background_videos = [f for f in os.listdir(self.background_videos_folder)
                             if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]

        if not background_videos:
            raise Exception("No background videos found! Please add videos to the background_videos folder.")

        return os.path.join(self.background_videos_folder, random.choice(background_videos))

    def get_random_audio_track(self):
        """Get a random audio track"""
        audio_tracks = [f for f in os.listdir(self.audios_folder)
                        if f.lower().endswith(('.mp3', '.wav', '.aac'))]

        if not audio_tracks:
            raise Exception("No audio tracks found! Please add audio files to the audio_tracks folder.")

        return os.path.join(self.audios_folder, random.choice(audio_tracks))

    def create_short_video(self, story):
        """Create a short video with the given story"""
        try:
            background_path = self.get_random_background_video()
            audio_path = self.get_random_audio_track()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"short_{timestamp}.mp4"

            return self._create_short_with_assets(story, background_path, audio_path, output_filename)

        except Exception as e:
            logging.error(f"Error creating short video: {e}")
            return None

    def create_long_story_video(self, story):
        """Create a 5-minute story video with TTS audio and synchronized text"""
        try:
            logging.info("Creating 5-minute story video...")

            # Generate TTS audio
            logging.info(f"Starting audio creation...")
            audio_path = self._generate_tts_audio(f"{story['title']}. {story['story']}")
            if not audio_path:
                logging.error("Failed to generate TTS audio")
                return None

            # Get background video
            background_path = self.get_random_background_video()

            background_music = self.get_random_audio_track()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"long_story_{timestamp}.mp4"

            ffmpeg_video_creator = FFMPEGVideoCreator()
            # Try thrice to create the video
            for attempt in range(3):
                logging.info(f"Attempt {attempt + 1} to create long story video...")
                op_video_path = ffmpeg_video_creator.create_video(
                    background_video=background_path,
                    voiceover=audio_path,
                    background_music=background_music,  # No background music for long story
                    output_file=os.path.join(self.long_output_folder, output_filename),
                    story_title=story['title'],
                    bg_music_volume=0.05,  # No music volume
                    quality="medium"
                )
                if op_video_path:
                    logging.info(f"Long story video created successfully: {op_video_path}")
                    return op_video_path
                else:
                    logging.error("Failed to create long story video. Waiting 10 secs before retrying...")
                    sleep(10)
        except Exception as e:
            logging.error(f"Error creating long story video: {e}")
            return None

    def _generate_tts_audio(self, text):
        """
        Synthesizes long input, writing the resulting audio to `output_gcs_uri`.

        Args:
            project_id: ID or number of the Google Cloud project you want to use.
            output_gcs_uri: Specifies a Cloud Storage URI for the synthesis results.
                Must be specified in the format:
                ``gs://bucket_name/object_name``, and the bucket must
                already exist.
        """

        client = texttospeech.TextToSpeechLongAudioSynthesizeClient()

        input = texttospeech.SynthesisInput(text=text)

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Chirp3-HD-Charon"
        )

        parent = f"projects/{os.environ['GCP_PROJECT_ID']}/locations/{os.environ['GCP_BUCKET_REGION']}"
        output_blob_name = f"audio/{datetime.now().strftime('%Y%m%d_%H%M%S')}_audio.wav"
        output_gcs_uri = f"gs://{os.environ['GCP_BUCKET_NAME']}/{os.environ['GCP_BUCKET_AUDIO_PATH']}/{output_blob_name}"

        request = texttospeech.SynthesizeLongAudioRequest(
            parent=parent,
            input=input,
            audio_config=audio_config,
            voice=voice,
            output_gcs_uri=output_gcs_uri,
        )

        operation = client.synthesize_long_audio(request=request)
        result = operation.result(timeout=300)
        logging.info(f"Finished processing. GCP location: {output_gcs_uri}")

        op_path = os.path.join(constants.DATA_DIR, 'generated_audio', 'temp_audio.wav')
        storage_client = storage.Client()
        bucket = storage_client.bucket(os.environ['GCP_BUCKET_NAME'])
        blob = bucket.blob(f"{os.environ['GCP_BUCKET_AUDIO_PATH']}/{output_blob_name}")
        blob.download_to_filename(op_path)
        logging.info(f"Downloaded storage object {output_gcs_uri} to local file {op_path}.")
        return op_path

    def _create_short_with_assets(self, story, background_video_path, audio_path, output_filename):
        """Create a video short with story overlay using specific assets"""
        try:
            # Load background video
            background = VideoFileClip(background_video_path)

            # Resize to 9:16 aspect ratio (1080x1920 for YouTube Shorts)
            background = background.resized(height=1920)
            if background.w > 1080:
                background = background.cropped(x_center=background.w / 2, width=1080)

            # Limit duration to CLIP_DURATION seconds max
            clip_duration = float(os.getenv('CLIP_DURATION', 20))
            if background.duration > clip_duration:
                background = background.with_duration(clip_duration)
            elif background.duration < clip_duration:
                background = background.with_effects([vfx.Loop()]).with_duration(clip_duration)

            # Load audio track
            audio_clip = AudioFileClip(audio_path)
            if audio_clip.duration < background.duration:
                audio_clip = audio_clip.with_effects([afx.AudioLoop(duration=background.duration)])
            elif audio_clip.duration > background.duration:
                audio_clip = audio_clip.with_duration(background.duration)

            # Create title clip
            wrapped_text = textwrap.fill(story['title'], width=30)
            title_clip = TextClip(
                text=wrapped_text,
                font=os.path.join(self.fonts_folder, os.getenv('FONT_PATH')),
                color='white',
                stroke_color='black',
                stroke_width=3,
                method='caption',
                size=(900, 300),
                font_size=90,
                text_align="center",
                interline=8,
                margin=(100, 50),
                duration=background.duration
            )

            # Create story clip
            wrapped_text = textwrap.fill(story['story'], width=30)
            story_clip = TextClip(
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
            logging.info("Creating video composite...")
            final_video = CompositeVideoClip([background, title_clip, story_clip])
            final_video = final_video.with_audio(audio_clip)

            # Export video
            output_path = os.path.join(self.output_folder, output_filename)
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