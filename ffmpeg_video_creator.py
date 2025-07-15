import subprocess
import os
import json
import shutil
import platform
import logging

class FFMPEGVideoCreator:
    def __init__(self):
        self.ffmpeg_path = self.find_ffmpeg()
        self.ffprobe_path = self.find_ffprobe()

    def find_ffmpeg(self):
        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        return ffmpeg

    def find_ffprobe(self):
        ffprobe = shutil.which("ffprobe") or "ffprobe"
        return ffprobe

    def validate_files(self, background_video, voiceover, background_music):
        files = {
            'Background Video': background_video,
            'Voiceover': voiceover,
            'Background Music': background_music
        }

        for name, filepath in files.items():
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"{name} file not found: {filepath}")
            print(f"✓ {name}: {filepath}")

    def get_media_info(self, filepath):
        try:
            cmd = [
                self.ffprobe_path, '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', filepath
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            print(f"Warning: Could not get info for {filepath}: {e}")
        return None

    def get_font_path(self):
        if platform.system() == "Windows":
            return "C\\:/Windows/Fonts/arialbd.ttf"  # Arial Bold on Windows
        else:
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Linux default

    def create_video(self, background_video, voiceover, background_music,
                     output_file="output_video.mp4", duration=None,
                     bg_music_volume=0.15, quality="medium",
                     story_title=""):

        # Validate files
        self.validate_files(background_video, voiceover, background_music)

        # Get media info
        logging.info("Analyzing input files...")
        voice_info = self.get_media_info(voiceover)

        # Determine video duration
        if voice_info:
            voice_duration = float(voice_info['format']['duration'])
            duration = int(voice_duration) + 5
            logging.info(f"Voiceover duration: {voice_duration:.2f} seconds")
            logging.info(f"Setting video duration to {duration} seconds (voiceover + 5 seconds)")
        else:
            duration = 305  # Fallback default

        # Quality presets
        quality_presets = {
            "fast": {"preset": "ultrafast", "crf": "28"},
            "medium": {"preset": "medium", "crf": "23"},
            "high": {"preset": "slow", "crf": "20"},
            "best": {"preset": "veryslow", "crf": "18"}
        }

        preset_settings = quality_presets.get(quality, quality_presets["medium"])

        # Set up drawtext filter for centered uppercase title
        font_path = self.get_font_path()
        story_title = story_title.upper()
        drawtext_filter = (
            f"drawtext=fontfile='{font_path}':text='{story_title}':"
            f"fontcolor=white:fontsize=80:box=1:boxcolor=black@0.5:boxborderw=20:"
            f"x=(w-text_w)/2:y=(h-text_h)/2"
        )

        filter_complex = (
            f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,setpts=PTS-STARTPTS,"
            f"{drawtext_filter}[video];"
            f"[2:a]volume={bg_music_volume},aloop=loop=-1:size=2e+09[bg_music];"
            f"[1:a]volume=1.0[voice];"
            f"[voice][bg_music]amix=inputs=2:duration=first:dropout_transition=3[audio]"
        )

        cmd = [
            self.ffmpeg_path,
            '-y',
            '-stream_loop', '-1',
            '-i', background_video,
            '-i', voiceover,
            '-i', background_music,
            '-filter_complex', filter_complex,
            '-map', '[video]',
            '-map', '[audio]',
            '-c:v', 'libx264',
            '-preset', preset_settings["preset"],
            '-crf', preset_settings["crf"],
            '-profile:v', 'high',
            '-level', '4.0',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '48000',
            '-t', str(duration),
            '-movflags', '+faststart',
            output_file
        ]

        logging.info(f"Creating video: {output_file}")
        logging.info(f"Duration: {duration} seconds")
        logging.info(f"Background music volume: {bg_music_volume * 100}%")
        logging.info(f"Quality: {quality}")
        logging.info(f"FFmpeg command: {" ".join(cmd)}")
        logging.info(f"Starting FFmpeg process to create video...")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            for line in process.stdout:
                if 'frame=' in line or 'time=' in line:
                    logging.info(f"\r{line.strip()}")

            process.wait()

            if process.returncode == 0:
                logging.info(f"✓ Video created successfully: {output_file}")

                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file) / (1024 * 1024)
                    logging.info(f"File size: {file_size:.2f} MB")

                return output_file
            else:
                logging.info(f"✗ Error: FFmpeg process failed with return code {process.returncode}")
                return None

        except KeyboardInterrupt:
            logging.info("Process interrupted by user")
            process.terminate()
            return None
        except Exception as e:
            logging.info(f"✗ Error running FFmpeg: {e}")
            return None
