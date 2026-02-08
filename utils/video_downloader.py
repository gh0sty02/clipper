import yt_dlp
from pathlib import Path
import logging
import re
from typing import Optional, Tuple, List, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoDownloader:
    """Download YouTube videos using yt-dlp with partial/segment support"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def download(self, youtube_url: str, video_id: str = None) -> dict:
        """
        Download full YouTube video (original method)
        
        Args:
            youtube_url: YouTube video URL
            video_id: Optional custom video ID for filename
            
        Returns:
            dict with 'path', 'title', 'duration', 'thumbnail'
        """
        
        if not video_id:
            video_id = self._extract_video_id(youtube_url)
        
        output_template = str(self.output_dir / f"{video_id}.%(ext)s")
        
        ydl_opts = {
            'format': (
                'bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/'
                'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/'
                'bestvideo[ext=webm][vcodec^=vp9]+bestaudio[ext=webm]/'
                'best[ext=mp4]/best'
            ),
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'prefer_free_formats': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'embedsubtitles': False,
            'postprocessors': [{
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': 'mp4',
            }],
            'postprocessor_args': {
                'merger': ['-sn'],
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Downloading full video: {youtube_url}")
                info = ydl.extract_info(youtube_url, download=True)
                
                filename = ydl.prepare_filename(info)
                
                return {
                    'path': filename,
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'vcodec': info.get('vcodec', ''),
                }
                
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise
    
    def download_segment(self, youtube_url: str, start_time: Union[str, float, int], 
                        end_time: Union[str, float, int], video_id: str = None,
                        force_keyframes: bool = False) -> dict:
        """
        Download ONLY a specific time segment of a YouTube video
        
        Args:
            youtube_url: YouTube video URL
            start_time: Start time (seconds, "HH:MM:SS", "MM:SS", or "SS")
            end_time: End time (same formats as start_time)
            video_id: Optional custom video ID for filename
            force_keyframes: If True, forces exact cuts (slower but frame-accurate)
            
        Returns:
            dict with 'path', 'title', 'duration', 'thumbnail', 'segment_start', 'segment_end'
        """
        
        if not video_id:
            video_id = self._extract_video_id(youtube_url)
        
        # Convert times to yt-dlp format
        start_str = self._format_time(start_time)
        end_str = self._format_time(end_time)
        
        # Create segment-specific filename
        safe_start = re.sub(r'[:.]', '-', str(start_time))
        safe_end = re.sub(r'[:.]', '-', str(end_time))
        output_template = str(self.output_dir / f"{video_id}_segment_{safe_start}_{safe_end}.%(ext)s")
        
        # Build download sections string
        # Format: "*start-end" (asterisk indicates time range, not chapter)
        download_sections = f"*{start_str}-{end_str}"
        
        ydl_opts = {
            'format': (
                'bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/'
                'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/'
                'bestvideo[ext=webm][vcodec^=vp9]+bestaudio[ext=webm]/'
                'best[ext=mp4]/best'
            ),
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'download_sections': [download_sections],  # ⭐ KEY PARAMETER
            'force_keyframes_at_cuts': force_keyframes,  # ⭐ For exact cuts
            'writesubtitles': False,
            'writeautomaticsub': False,
            'embedsubtitles': False,
            'postprocessor_args': {
                'merger': ['-sn'],
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Downloading segment {start_str}-{end_str} from: {youtube_url}")
                info = ydl.extract_info(youtube_url, download=True)
                
                filename = ydl.prepare_filename(info)
                
                # Calculate actual segment duration
                segment_duration = self._time_to_seconds(end_time) - self._time_to_seconds(start_time)
                
                return {
                    'path': filename,
                    'title': info.get('title', ''),
                    'duration': segment_duration,
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'vcodec': info.get('vcodec', ''),
                    'segment_start': start_str,
                    'segment_end': end_str,
                    'full_duration': info.get('duration', 0),
                }
                
        except Exception as e:
            logger.error(f"Error downloading segment: {str(e)}")
            raise
    
    def download_multiple_segments(self, youtube_url: str, 
                                   segments: List[Tuple[Union[str, float, int], Union[str, float, int]]],
                                   video_id: str = None,
                                   merge: bool = False) -> List[dict]:
        """
        Download multiple segments from a video
        
        Args:
            youtube_url: YouTube video URL
            segments: List of (start_time, end_time) tuples
            video_id: Optional custom video ID
            merge: If True, merge all segments into single file (requires FFmpeg)
            
        Returns:
            List of dicts for each segment, or single dict if merge=True
        """
        
        results = []
        
        for i, (start, end) in enumerate(segments):
            result = self.download_segment(
                youtube_url, 
                start, 
                end, 
                video_id=f"{video_id or 'video'}_part{i+1}" if not merge else video_id
            )
            results.append(result)
        
        if merge and len(results) > 1:
            # Merge segments using FFmpeg
            merged_path = self._merge_segments(results, video_id)
            return [{
                'path': merged_path,
                'segments': results,
                'merged': True
            }]
        
        return results
    
    def download_with_crop(self, youtube_url: str, start_time: Union[str, float, int],
                          end_time: Union[str, float, int], crop_x: int,
                          video_height: int = 1080, video_width: int = 1920,
                          video_id: str = None) -> dict:
        """
        Download segment AND apply crop in one operation (requires FFmpeg)
        
        Args:
            youtube_url: YouTube video URL
            start_time: Start time
            end_time: End time
            crop_x: X position for crop (center of crop window)
            video_height: Original video height
            video_width: Original video width
            video_id: Optional custom video ID
            
        Returns:
            dict with 'path' to cropped video
        """
        
        # First download the segment
        segment_info = self.download_segment(youtube_url, start_time, end_time, video_id)
        
        # Calculate crop parameters for 9:16 aspect ratio
        crop_width = int(video_height * 9 / 16)
        x_start = int(crop_x - crop_width / 2)
        x_start = max(0, min(x_start, video_width - crop_width))
        
        # Apply crop using FFmpeg
        input_path = segment_info['path']
        output_path = str(Path(input_path).with_suffix('')) + "_cropped.mp4"
        
        import subprocess
        
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-vf', f"crop={crop_width}:{video_height}:{x_start}:0,scale=1080:1920",
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-movflags', '+faststart',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Cropped video saved to: {output_path}")
            
            # Clean up original segment if desired
            # Path(input_path).unlink()
            
            return {
                **segment_info,
                'path': output_path,
                'cropped': True,
                'crop_x': crop_x,
                'aspect_ratio': '9:16'
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg crop failed: {e.stderr}")
            raise
    
    def get_stream_url(self, youtube_url: str) -> dict:
        """
        Extract direct stream URL without downloading.

        Returns:
            dict with 'video_url', 'audio_url', 'title', 'duration'
        """
        ydl_opts = {
            'format': (
                'bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/'
                'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/'
                'best[ext=mp4]/best'
            ),
            'quiet': True,
            'no_warnings': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

            # Get the selected format URLs
            requested_formats = info.get('requested_formats', [])
            if requested_formats:
                video_url = requested_formats[0]['url']
                audio_url = requested_formats[1]['url'] if len(requested_formats) > 1 else video_url
            else:
                video_url = info['url']
                audio_url = info['url']

            return {
                'video_url': video_url,
                'audio_url': audio_url,
                'title': info.get('title', ''),
                'duration': info.get('duration', 0),
            }

    def _format_time(self, time_val: Union[str, float, int]) -> str:
        """Convert various time formats to yt-dlp string format"""
        if isinstance(time_val, str):
            # Already formatted (e.g., "2:35", "00:04:22")
            return time_val
        
        # Convert seconds to HH:MM:SS or MM:SS
        seconds = int(time_val)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def _time_to_seconds(self, time_val: Union[str, float, int]) -> int:
        """Convert time to seconds for duration calculation"""
        if isinstance(time_val, (int, float)):
            return int(time_val)
        
        # Parse "HH:MM:SS", "MM:SS", or "SS"
        parts = str(time_val).split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return int(parts[0])
    
    def _merge_segments(self, segment_results: List[dict], video_id: str) -> str:
        """Merge multiple video segments using FFmpeg concat"""
        import subprocess
        
        # Create concat list file
        list_file = self.output_dir / f"{video_id}_concat_list.txt"
        with open(list_file, 'w') as f:
            for seg in segment_results:
                f.write(f"file '{seg['path']}'\n")
        
        output_path = str(self.output_dir / f"{video_id}_merged.mp4")
        
        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(list_file),
            '-c', 'copy',
            output_path
        ]
        
        subprocess.run(cmd, check=True)
        list_file.unlink()  # Clean up list file
        
        return output_path
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'^([0-9A-Za-z_-]{11})$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from URL: {url}")


# Example usage
if __name__ == "__main__":
    downloader = VideoDownloader(output_dir=Path("./downloads"))
    
    url = "https://www.youtube.com/watch?v=example"
    
    # Example 1: Download specific segment (2:35 to 4:22)
    result = downloader.download_segment(
        youtube_url=url,
        start_time="2:35",      # or 155 (seconds)
        end_time="4:22",        # or 262 (seconds)
        video_id="test_video",
        force_keyframes=False   # Set True for exact frame cuts (slower)
    )
    print(f"Downloaded segment: {result}")
    
    # Example 2: Download multiple segments
    segments = [
        ("0:00", "0:30"),   # First 30 seconds
        ("2:35", "4:22"),   # Middle section
        ("10:00", "10:15")  # End highlight
    ]
    results = downloader.download_multiple_segments(url, segments, merge=True)
    
    # Example 3: Download + crop in one go (for your Clipper pipeline)
    result = downloader.download_with_crop(
        youtube_url=url,
        start_time="2:35",
        end_time="4:22",
        crop_x=960,  # Center of 1920 width
        video_width=1920,
        video_height=1080
    )