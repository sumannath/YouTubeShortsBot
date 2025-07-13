import os
import random
import textwrap
import logging
import re
import json
import tempfile
from datetime import datetime
from moviepy import VideoFileClip, TextClip, AudioFileClip, CompositeVideoClip
from moviepy import afx, vfx
from config import constants
import azure.cognitiveservices.speech as speechsdk
from pydub import AudioSegment
import nltk
from nltk.tokenize import sent_tokenize
import warnings

warnings.filterwarnings("ignore")

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')


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
            audio_path = self._generate_tts_audio(story['story'])
            if not audio_path:
                logging.error("Failed to generate TTS audio")
                return None

            # Get background video
            background_path = self.get_random_background_video()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"long_story_{timestamp}.mp4"

            return self._create_long_video_with_sync(story, background_path, audio_path, output_filename)

        except Exception as e:
            logging.error(f"Error creating long story video: {e}")
            return None

    def _generate_tts_audio(self, text):
        """Generate TTS audio using Azure Speech Service"""
        try:
            if not self.azure_key:
                logging.error("Azure Speech key not configured")
                return None

            # Configure speech service
            speech_config = speechsdk.SpeechConfig(
                endpoint=self.azure_endpoint,
                subscription=self.azure_key
            )
            speech_config.speech_synthesis_voice_name = self.azure_voice

            # Create temporary audio file
            temp_audio_path = os.path.join(tempfile.gettempdir(), f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")

            # Configure audio output
            audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_audio_path)

            # Create synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config
            )

            # Add SSML for better speech control
            ssml_text = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
                <voice name="{self.azure_voice}">
                    <prosody rate="0.9" pitch="medium" volume="medium">
                        {text}
                    </prosody>
                </voice>
            </speak>
            """

            logging.info("Synthesizing speech...")
            result = synthesizer.speak_ssml_async(ssml_text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logging.info(f"TTS audio generated successfully: {temp_audio_path}")
                return temp_audio_path
            else:
                logging.error(f"TTS failed: {result.reason}")
                return None

        except Exception as e:
            logging.error(f"Error generating TTS audio: {e}")
            return None

    def _split_text_into_segments(self, text, max_lines=4):
        """Split text into segments of 3-4 lines each"""
        sentences = sent_tokenize(text)
        segments = []
        current_segment = []
        current_lines = 0

        for sentence in sentences:
            # Wrap sentence and count lines
            wrapped_sentence = textwrap.fill(sentence, width=35)
            sentence_lines = len(wrapped_sentence.split('\n'))

            # If adding this sentence would exceed max lines, start new segment
            if current_lines + sentence_lines > max_lines and current_segment:
                segments.append(' '.join(current_segment))
                current_segment = [sentence]
                current_lines = sentence_lines
            else:
                current_segment.append(sentence)
                current_lines += sentence_lines

        # Add remaining segment
        if current_segment:
            segments.append(' '.join(current_segment))

        return segments

    def _estimate_audio_timings(self, text_segments, total_duration):
        """Estimate timing for each text segment based on character count"""
        total_chars = sum(len(segment) for segment in text_segments)
        timings = []
        current_time = 0

        for segment in text_segments:
            # Calculate duration proportional to character count
            segment_duration = (len(segment) / total_chars) * total_duration
            timings.append((current_time, current_time + segment_duration))
            current_time += segment_duration

        return timings

    def _create_long_video_with_sync(self, story, background_path, audio_path, output_filename):
        """Create synchronized long video with TTS audio"""
        try:
            # Load and prepare background video
            background = VideoFileClip(background_path)

            # Get audio duration
            audio_clip = AudioFileClip(audio_path)
            target_duration = audio_clip.duration

            logging.info(f"Audio duration: {target_duration:.2f} seconds")

            # Resize background to 9:16 aspect ratio
            background = background.resized(height=1920)
            if background.w > 1080:
                background = background.cropped(x_center=background.w / 2, width=1080)

            # Loop background video to match audio duration
            if background.duration < target_duration:
                background = background.with_effects([vfx.Loop()]).with_duration(target_duration)
            else:
                background = background.with_duration(target_duration)

            # Create title clip (shown for first 3 seconds)
            title_text = textwrap.fill(story['title'], width=30)
            title_clip = TextClip(
                text=title_text,
                font=os.path.join(self.fonts_folder, os.getenv('FONT_PATH')),
                color='white',
                stroke_color='black',
                stroke_width=3,
                method='caption',
                size=(900, 400),
                font_size=80,
                text_align="center",
                interline=10,
                margin=(100, 50)
            ).with_position('center').with_duration(3)

            # Split story into segments
            text_segments = self._split_text_into_segments(story['story'])

            # Calculate timings (start after title)
            story_duration = target_duration - 3
            timings = self._estimate_audio_timings(text_segments, story_duration)

            # Create text clips for each segment
            text_clips = []
            for i, (segment, (start_time, end_time)) in enumerate(zip(text_segments, timings)):
                wrapped_text = textwrap.fill(segment, width=35)

                text_clip = TextClip(
                    text=wrapped_text,
                    font=os.path.join(self.fonts_folder, os.getenv('FONT_PATH')),
                    color='white',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(900, 800),
                    font_size=60,
                    text_align="center",
                    interline=8,
                    margin=(100, 50)
                ).with_position('center').with_start(start_time + 3).with_duration(end_time - start_time)

                text_clips.append(text_clip)

            # Compose final video
            logging.info("Creating video composite...")
            all_clips = [background, title_clip] + text_clips
            final_video = CompositeVideoClip(all_clips)
            final_video = final_video.with_audio(audio_clip)

            # Export video
            output_path = os.path.join(self.long_output_folder, output_filename)
            final_video.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio=True,
                audio_codec='aac',
                temp_audiofile=os.path.join(constants.DATA_DIR, 'temp-long-audio.m4a'),
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

            # Clean up temporary audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)

            logging.info(f"Long video created successfully: {output_path}")
            return output_path

        except Exception as e:
            logging.error(f"Error creating long video: {e}")
            return None

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