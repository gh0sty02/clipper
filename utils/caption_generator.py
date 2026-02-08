from pathlib import Path
import logging
from config import CAPTION_PRESETS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CaptionGenerator:
    """Generate ASS subtitle files for video captions"""
    
    def __init__(self, preset: str = 'minimal'):
        if preset not in CAPTION_PRESETS:
            raise ValueError(f"Invalid preset: {preset}. Choose from {list(CAPTION_PRESETS.keys())}")
        
        self.preset = CAPTION_PRESETS[preset]
        self.preset_name = preset
    
    def generate_ass_file(self, transcript_segments: list, output_path: Path) -> Path:
        """
        Generate ASS subtitle file from transcript segments

        Args:
            transcript_segments: List of dicts with 'text', 'start', 'duration'
            output_path: Path to save .ass file

        Returns:
            Path to generated .ass file
        """

        ass_content = self._create_ass_header()

        # Split segments if max_words is set
        max_words = self.preset.get('max_words')
        if max_words:
            transcript_segments = self._split_segments(transcript_segments, max_words)

        # Remove overlapping timestamps - each caption ends when next begins
        transcript_segments = self._remove_overlaps(transcript_segments)

        for segment in transcript_segments:
            ass_content += self._create_dialogue_line(
                text=segment['text'],
                start=segment['start'],
                duration=segment['duration']
            )

        output_path = Path(output_path)
        output_path.write_text(ass_content, encoding='utf-8')

        logger.info(f"Generated ASS subtitle file: {output_path}")
        return output_path

    def _split_segments(self, segments: list, max_words: int) -> list:
        """Split segments that have more than max_words into smaller chunks"""
        result = []
        max_duration = 2.5  # Cap duration at 2.5 seconds per caption

        for segment in segments:
            words = segment['text'].split()

            if len(words) <= max_words:
                # Cap duration even for short segments
                capped_duration = min(segment['duration'], max_duration)
                result.append({
                    'text': segment['text'],
                    'start': segment['start'],
                    'duration': capped_duration
                })
            else:
                # Split into chunks
                chunks = [words[i:i + max_words] for i in range(0, len(words), max_words)]
                chunk_duration = min(segment['duration'] / len(chunks), max_duration)

                for i, chunk in enumerate(chunks):
                    result.append({
                        'text': ' '.join(chunk),
                        'start': segment['start'] + (i * chunk_duration),
                        'duration': chunk_duration
                    })

        return result

    def _remove_overlaps(self, segments: list) -> list:
        """Adjust timings so captions don't overlap and have clean transitions"""
        if not segments:
            return segments

        gap = 0.05  # 50ms gap between captions for clean transition

        for i in range(len(segments) - 1):
            next_start = segments[i + 1]['start']
            # End current segment before next one starts (with gap)
            max_duration = next_start - segments[i]['start'] - gap
            if segments[i]['duration'] > max_duration:
                segments[i]['duration'] = max(0.1, max_duration)

        return segments
    
    def _create_ass_header(self) -> str:
        """Create ASS file header with styling"""

        # Position mapping
        position_map = {
            'bottom': 2,    # Bottom center
            'lower': 2,     # Lower area (uses custom margin)
            'center': 5,    # Middle center
            'top': 8        # Top center
        }

        alignment = position_map.get(self.preset.get('position', 'bottom'), 2)
        margin_v = self.preset.get('margin_v', 120 if alignment == 2 else 10)

        header = f"""[Script Info]
Title: Clipper Auto-Generated Captions
ScriptType: v4.00+
WrapStyle: 2
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.preset.get('font', 'Arial')},{self.preset.get('size', 24)},{self.preset.get('color', '&HFFFFFF&')},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{self.preset.get('outline', 2)},{self.preset.get('shadow', 0)},{alignment},40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        return header
    
    @staticmethod
    def _clean_caption_text(text: str) -> str:
        """Clean and format caption text from auto-generated transcripts"""
        import re

        text = text.replace('\n', ' ').strip()

        # Remove filler artifacts common in auto-captions
        text = re.sub(r'\[.*?\]', '', text)  # [Music], [Applause], etc.

        # Capitalize first letter of each sentence
        text = re.sub(r'(^|[.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)

        # Capitalize the very first character
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        # Capitalize "I" when standalone
        text = re.sub(r'\bi\b', 'I', text)

        return text.strip()

    def _create_dialogue_line(self, text: str, start: float, duration: float) -> str:
        """Create a single dialogue line in ASS format"""

        start_time = self._seconds_to_ass_time(start)
        end_time = self._seconds_to_ass_time(start + duration)

        # Clean text
        text = self._clean_caption_text(text)
        
        # Add word-by-word animation for 'bold' preset
        if self.preset_name == 'bold':
            words = text.split()
            animated_text = self._create_word_animation(words, duration)
            text = animated_text
        
        return f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
    
    def _create_word_animation(self, words: list, total_duration: float) -> str:
        """Create word-by-word highlight animation"""
        # For now, return simple text
        # TODO: Implement karaoke-style word highlighting
        return ' '.join(words)
    
    @staticmethod
    def _seconds_to_ass_time(seconds: float) -> str:
        """Convert seconds to ASS time format (H:MM:SS.CC)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)
        
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


# Example usage
if __name__ == "__main__":
    from utils.transcript_fetcher import TranscriptFetcher
    
    # Fetch transcript
    fetcher = TranscriptFetcher()
    transcript = fetcher.fetch_transcript("dQw4w9WgXcQ")
    
    # Generate captions
    generator = CaptionGenerator(preset='bold')
    
    # Filter transcript for specific time range (3-5 minutes)
    filtered = [seg for seg in transcript if 180 <= seg['start'] <= 300]
    
    output_file = Path("output.ass")
    generator.generate_ass_file(filtered, output_file)
    
    print(f"Generated: {output_file}")