import yt_dlp
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoDownloader:
    """Download YouTube videos using yt-dlp"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def download(self, youtube_url: str, video_id: str = None) -> dict:
        """
        Download YouTube video
        
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
            # ⭐ KEY FIX: Avoid AV1, prefer H.264/VP9
            'format': (
                'bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/'  # H.264 + AAC
                'bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/'   # H.264 variants
                'bestvideo[ext=webm][vcodec^=vp9]+bestaudio[ext=webm]/' # VP9 fallback
                'best[ext=mp4]/best'                                     # Final fallback
            ),
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'prefer_free_formats': False,  # Don't prefer WebM over MP4
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Downloading video: {youtube_url}")
                info = ydl.extract_info(youtube_url, download=True)
                
                filename = ydl.prepare_filename(info)
                
                return {
                    'path': filename,
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'vcodec': info.get('vcodec', ''),  # Added for debugging
                }
                
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        import re
        
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