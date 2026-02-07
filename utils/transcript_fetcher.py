from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptFetcher:
    """Fetch transcripts from YouTube videos"""
    
    @staticmethod
    def extract_video_id(url: str) -> str:
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
    
    def fetch_transcript(self, youtube_url: str, languages: list = None) -> list:
        """
        Fetch transcript from YouTube video

        Args:
            youtube_url: YouTube video URL or video ID
            languages: List of language codes to try (default: ['en'])

        Returns:
            List of transcript segments with 'text', 'start', 'duration'
        """
        if languages is None:
            languages = ['en', 'en-US', 'en-GB']

        try:
            video_id = self.extract_video_id(youtube_url)
            logger.info(f"Fetching transcript for video ID: {video_id}")

            # youtube-transcript-api v1.x uses instance methods
            api = YouTubeTranscriptApi()
            transcript_data = api.fetch(video_id, languages=languages)

            # Convert to list of dicts with expected keys
            result = []
            for snippet in transcript_data:
                result.append({
                    'text': snippet.text,
                    'start': snippet.start,
                    'duration': snippet.duration
                })

            logger.info(f"Successfully fetched transcript with {len(result)} segments")
            return result

        except TranscriptsDisabled:
            logger.error("Transcripts are disabled for this video")
            raise
        except NoTranscriptFound:
            logger.error("No transcript found for this video")
            raise
        except Exception as e:
            logger.error(f"Error fetching transcript: {str(e)}")
            raise
    
    def format_transcript(self, transcript_data: list) -> str:
        """
        Format transcript data into readable text
        
        Args:
            transcript_data: List of transcript segments
            
        Returns:
            Formatted transcript string
        """
        formatted_lines = []
        
        for segment in transcript_data:
            timestamp = self._seconds_to_timestamp(segment['start'])
            text = segment['text'].strip()
            formatted_lines.append(f"[{timestamp}] {text}")
        
        return '\n'.join(formatted_lines)
    
    def get_segment_at_time(self, transcript_data: list, start_time: float, end_time: float) -> str:
        """
        Get transcript segment between start and end time
        
        Args:
            transcript_data: List of transcript segments
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            Transcript text for that time range
        """
        segments = []
        
        for segment in transcript_data:
            seg_start = segment['start']
            seg_end = seg_start + segment['duration']
            
            # Check if segment overlaps with requested time range
            if seg_start < end_time and seg_end > start_time:
                segments.append(segment['text'])
        
        return ' '.join(segments)
    
    @staticmethod
    def _seconds_to_timestamp(seconds: float) -> str:
        """Convert seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _seconds_to_srt_timestamp(seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def to_srt(self, transcript_data: list) -> str:
        """
        Convert transcript data to SRT format

        Args:
            transcript_data: List of transcript segments

        Returns:
            SRT formatted string
        """
        srt_lines = []

        for idx, segment in enumerate(transcript_data, start=1):
            start_time = segment['start']
            end_time = start_time + segment['duration']

            start_ts = self._seconds_to_srt_timestamp(start_time)
            end_ts = self._seconds_to_srt_timestamp(end_time)

            srt_lines.append(str(idx))
            srt_lines.append(f"{start_ts} --> {end_ts}")
            srt_lines.append(segment['text'].strip())
            srt_lines.append("")  # Blank line between entries

        return '\n'.join(srt_lines)

    def save_srt(self, transcript_data: list, output_path: str) -> None:
        """
        Save transcript as SRT file

        Args:
            transcript_data: List of transcript segments
            output_path: Path to save the SRT file
        """
        srt_content = self.to_srt(transcript_data)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        logger.info(f"Saved SRT file to: {output_path}")


# Example usage
if __name__ == "__main__":
    fetcher = TranscriptFetcher()
    
    # Fetch transcript
    transcript = fetcher.fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Format and print
    formatted = fetcher.format_transcript(transcript)
    print(formatted[:500])  # Print first 500 chars
    
    # Get specific time segment
    segment = fetcher.get_segment_at_time(transcript, 30, 60)
    print(f"\nSegment (30-60s): {segment}")