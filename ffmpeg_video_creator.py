import json
import logging
import os
import subprocess

from config import constants


class FFMPEGVideoCreator:
    def __init__(self):
        self.ffmpeg_docker_image = "linuxserver/ffmpeg"

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
                'docker', 'run', '--rm',
                '-v', f"{constants.ASSETS_DIR}:/assets",
                '-v', f"{constants.DATA_DIR}:/data",
                '--entrypoint', 'ffprobe',
                self.ffmpeg_docker_image,
                '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', f"/data/generated_audio/{os.path.basename(filepath)}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            logging.info(f"FFProbe command: {" ".join(cmd)}")
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            print(f"Warning: Could not get info for {filepath}: {e}")
        return None

    def get_font_path(self):
        return "/assets/fonts/Lato/Lato-Regular.ttf"

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

        cmd = ["docker", "run", "--rm"]

        if os.environ['ENV'] == 'prod':
            cmd += [
                "--device=/dev/dri:/dev/dri",
                "-hwaccel", "qsv",
            ]

        cmd += [
            '-v', f"{constants.ASSETS_DIR}:/assets",
            '-v', f"{constants.DATA_DIR}:/data",
            self.ffmpeg_docker_image,
            '-y',
            '-stream_loop', '-1',
            "-i", f"/assets/background_videos/{os.path.basename(background_video)}",
            "-i", f"/data/generated_audio/{os.path.basename(voiceover)}",
            "-i", f"/assets/audio_tracks/{os.path.basename(background_music)}",
            "-filter_complex", filter_complex,
            '-map', '[video]',
            '-map', '[audio]'
        ]

        if os.environ['ENV'] == 'prod':
            cmd += [
                '-c:v', 'h264_qsv',
            ]
        else:
            cmd += [
                '-c:v', 'libx264',
            ]

        cmd += [
            '-preset', preset_settings["preset"],
            '-crf', preset_settings["crf"],
            '-profile:v', 'high',
            '-level', '4.0',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '48000',
            '-t', str(duration),
            '-movflags', '+faststart',
            f"/data/generated_long_videos/{os.path.basename(output_file)}"
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
