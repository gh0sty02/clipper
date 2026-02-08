import subprocess
from pathlib import Path
import logging
from config import (
    OUTPUT_RESOLUTIONS,
    FFMPEG_PRESET,
    FFMPEG_CRF,
    AUDIO_BITRATE
)
from utils.crop_detector import CropDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoProcessor:
    """Process video clips with cropping, trimming, and captions"""
    
    def __init__(self):
        self.crop_detector = CropDetector(face_detection_enabled=True, use_mediapipe=True)
    
    def create_clip(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        aspect_ratio: str = 'vertical',
        crop_method: str = 'auto',
        subtitle_file: str = None,
        audio_url: str = None
    ) -> dict:
        """
        Create a video clip with specified parameters

        Args:
            input_path: Path to source video or stream URL
            output_path: Path for output clip
            start_time: Start time in seconds
            end_time: End time in seconds
            aspect_ratio: 'vertical', 'square', or 'horizontal'
            crop_method: 'auto', 'center', 'cropdetect', or 'face'
            subtitle_file: Optional path to .ass subtitle file
            audio_url: Separate audio stream URL (for stream-based downloads)

        Returns:
            dict with processing info
        """

        duration = end_time - start_time

        # Get video info
        video_info = self._get_video_info(input_path)
        original_width = video_info['width']
        original_height = video_info['height']

        # Determine target resolution
        target_width, target_height = OUTPUT_RESOLUTIONS[aspect_ratio]

        # Detect optimal crop position
        logger.info(f"Detecting crop position using method: {crop_method}")
        crop_x, method_used = self.crop_detector.detect_crop_position(
            input_path,
            start_time,
            duration,
            method=crop_method
        )

        # Calculate crop dimensions
        crop_width = int(original_height * target_width / target_height)
        crop_height = original_height

        # Ensure crop fits within video bounds
        crop_x = max(0, min(crop_x - crop_width // 2, original_width - crop_width))

        logger.info(f"Cropping: {crop_width}x{crop_height} at position {crop_x},0")

        # Build filter chain
        vf_filters = []

        # Crop filter
        vf_filters.append(f"crop={crop_width}:{crop_height}:{crop_x}:0")

        # Scale to target resolution
        vf_filters.append(f"scale={target_width}:{target_height}")

        # Add subtitles if provided (use 'ass' filter instead of 'subtitles'
        # to avoid rendering embedded subtitle streams from the input)
        if subtitle_file:
            # Escape path for FFmpeg
            subtitle_path = Path(subtitle_file).absolute()
            subtitle_path_str = str(subtitle_path).replace('\\', '/').replace(':', '\\:')
            vf_filters.append(f"ass='{subtitle_path_str}'")

        vf_string = ','.join(vf_filters)

        # Build FFmpeg command
        cmd = ['ffmpeg', '-ss', str(start_time)]

        # Add video input
        cmd += ['-i', input_path]

        # Add separate audio input if provided (stream-based)
        if audio_url:
            cmd += ['-ss', str(start_time), '-i', audio_url]

        cmd += [
            '-t', str(duration),
            '-vf', vf_string,
            '-c:v', 'libx264',
            '-preset', FFMPEG_PRESET,
            '-crf', str(FFMPEG_CRF),
            '-c:a', 'aac',
            '-b:a', AUDIO_BITRATE,
        ]

        # Explicitly map only video and audio streams (strip all subtitle streams)
        if audio_url:
            cmd += ['-map', '0:v:0', '-map', '1:a:0']
        else:
            cmd += ['-map', '0:v:0', '-map', '0:a:0']

        cmd += ['-sn', '-dn', '-y', output_path]

        logger.info(f"Processing clip: {Path(output_path).name}")
        logger.info(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info(f"Successfully created clip: {output_path}")

            return {
                'success': True,
                'output_path': output_path,
                'duration': duration,
                'crop_method': method_used,
                'crop_position': crop_x,
                'resolution': f"{target_width}x{target_height}"
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise
    
    def _get_video_info(self, video_path: str) -> dict:
        """Get video metadata using ffprobe"""
        
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,bit_rate',
            '-of', 'csv=p=0',
            video_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            parts = result.stdout.strip().split(',')
            
            return {
                'width': int(parts[0]),
                'height': int(parts[1]),
                'duration': float(parts[2]) if len(parts) > 2 else 0,
                'bit_rate': int(parts[3]) if len(parts) > 3 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            raise


# Example usage
if __name__ == "__main__":
    from config import TEMP_DIR, OUTPUT_DIR
    
    processor = VideoProcessor()
    
    result = processor.create_clip(
        input_path=str(TEMP_DIR / "input.mp4"),
        output_path=str(OUTPUT_DIR / "clip_vertical.mp4"),
        start_time=180,  # 3:00
        end_time=300,    # 5:00
        aspect_ratio='vertical',
        crop_method='auto'
    )
    
    print(f"Result: {result}")