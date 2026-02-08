import sys
import json
import re
from pathlib import Path
import logging
from config import TEMP_DIR, OUTPUT_DIR
from utils.video_downloader import VideoDownloader
from utils.transcript_fetcher import TranscriptFetcher
from utils.segment_analyzer import SegmentAnalyzer
from utils.video_processor import VideoProcessor
from utils.caption_generator import CaptionGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
SEGMENTS_FILE = BASE_DIR / "segments.json"


def parse_srt_timestamp(ts: str) -> float:
    """Parse SRT-style timestamp to seconds. Supports HH:MM:SS,mmm / HH:MM:SS / MM:SS"""
    ts = ts.strip()
    ts = ts.replace(',', '.')

    parts = ts.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        return float(parts[0])


def load_segments(segments_path: Path) -> list:
    """Load clips from segments.json and convert timestamps to seconds"""
    with open(segments_path, 'r') as f:
        data = json.load(f)

    clips = []
    for seg in data['clips']:
        start = parse_srt_timestamp(seg['timestamp_start'])
        end = parse_srt_timestamp(seg['timestamp_end'])
        clips.append({
            'start_time': start,
            'end_time': end,
            'title': seg.get('suggested_title', ''),
            'viral_score': seg.get('viral_score', 0),
        })

    # Sort by viral score descending
    clips.sort(key=lambda c: c['viral_score'], reverse=True)
    return clips


class ClipperPipeline:
    """Complete pipeline for creating clips from YouTube videos"""

    def __init__(self):
        self.downloader = VideoDownloader(TEMP_DIR)
        self.transcript_fetcher = TranscriptFetcher()
        self.segment_analyzer = SegmentAnalyzer()
        self.video_processor = VideoProcessor()

    def process(
        self,
        youtube_url: str,
        output_dir: Path = OUTPUT_DIR,
        aspect_ratio: str = 'vertical',
        caption_preset: str = 'bold',
        segments_file: Path = None,
    ) -> list:
        """
        Full pipeline:
          1. Fetch transcript + save full transcript/SRT
          2. LLM analysis to find viral segments (or load from file)
          3. Download only needed segments from YouTube
          4. Crop, caption, output

        Args:
            youtube_url: YouTube video URL
            output_dir: Directory for output clips
            aspect_ratio: 'vertical', 'square', or 'horizontal'
            caption_preset: Caption style ('minimal', 'bold', etc.)
            segments_file: Optional pre-existing segments.json (skips LLM step)

        Returns:
            List of result dicts per clip
        """
        logger.info(f"Starting pipeline for: {youtube_url}")

        # Clean output directory
        if output_dir.exists():
            for f in output_dir.iterdir():
                if f.is_file():
                    f.unlink()
            logger.info(f"Cleared output directory: {output_dir}")

        # --- Step 1: Fetch transcript ---
        logger.info("Step 1: Fetching transcript...")
        transcript_data = None
        srt_content = None
        try:
            transcript_data = self.transcript_fetcher.fetch_transcript(youtube_url)

            # Save full transcript text
            full_txt = output_dir / "full_transcript.txt"
            full_txt.write_text(
                self.transcript_fetcher.format_transcript(transcript_data),
                encoding='utf-8'
            )
            logger.info(f"Saved full transcript: {full_txt}")

            # Save full SRT
            full_srt = output_dir / "full_transcript.srt"
            srt_content = self.transcript_fetcher.to_srt(transcript_data)
            full_srt.write_text(srt_content, encoding='utf-8')
            logger.info(f"Saved full SRT: {full_srt}")

        except Exception as e:
            logger.warning(f"Could not fetch transcript: {e}")
            logger.warning("Proceeding without captions")
            caption_preset = None

        # --- Step 2: LLM viral segment analysis ---
        if segments_file and segments_file.exists():
            logger.info(f"Step 2: Using existing segments file: {segments_file}")
        else:
            segments_file = output_dir / "segments.json"

            if not srt_content:
                logger.error("No transcript available for LLM analysis. Cannot identify segments.")
                return []

            logger.info("Step 2: Analyzing transcript with LLM for viral segments...")
            try:
                self.segment_analyzer.analyze_and_save(srt_content, segments_file)
            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")
                return []

        clips = load_segments(segments_file)
        logger.info(f"Loaded {len(clips)} clips (sorted by viral score)")

        # --- Step 3: Extract stream URLs (no download) ---
        logger.info("Step 3: Extracting stream URLs...")
        try:
            stream_info = self.downloader.get_stream_url(youtube_url)
            video_url = stream_info['video_url']
            audio_url = stream_info['audio_url']
            logger.info(f"Got stream URLs for: {stream_info['title']}")
        except Exception as e:
            logger.error(f"Failed to get stream URLs: {e}")
            return []

        # --- Step 4: Stream segments, crop & caption each clip ---
        logger.info(f"Step 4: Cropping & captioning {len(clips)} clips...")
        results = []

        for i, clip in enumerate(clips, 1):
            start_sec = clip['start_time']
            end_sec = clip['end_time']
            clip_duration = end_sec - start_sec
            safe_title = re.sub(r'[^\w\s-]', '', clip.get('title', '')).strip().replace(' ', '_')[:50]
            clip_name = f"clip_{i}_{safe_title}.mp4"
            output_path = output_dir / clip_name

            logger.info(f"[{i}/{len(clips)}] {clip.get('title', '')} "
                         f"({start_sec:.1f}s - {end_sec:.1f}s, score={clip['viral_score']})")

            # Generate subtitles
            subtitle_file = None
            if caption_preset and transcript_data:
                clip_transcript = [
                    {
                        'text': seg['text'],
                        'start': seg['start'] - start_sec,
                        'duration': seg['duration']
                    }
                    for seg in transcript_data
                    if start_sec <= seg['start'] <= end_sec
                ]

                if clip_transcript:
                    caption_gen = CaptionGenerator(preset=caption_preset)
                    subtitle_file = TEMP_DIR / f"clip_{i}.ass"
                    caption_gen.generate_ass_file(clip_transcript, subtitle_file)

                    # Save per-clip SRT
                    srt_name = f"clip_{i}_{safe_title}.srt"
                    self.transcript_fetcher.save_srt(clip_transcript, str(output_dir / srt_name))

            # Stream segment directly from YouTube, crop & process
            try:
                result = self.video_processor.create_clip(
                    input_path=video_url,
                    output_path=str(output_path),
                    start_time=start_sec,
                    end_time=end_sec,
                    aspect_ratio=aspect_ratio,
                    crop_method='auto',
                    subtitle_file=str(subtitle_file) if subtitle_file else None,
                    audio_url=audio_url
                )

                results.append({
                    **result,
                    'clip_number': i,
                    'title': clip.get('title', ''),
                    'viral_score': clip['viral_score'],
                    'has_captions': subtitle_file is not None
                })

            except Exception as e:
                logger.error(f"Failed to process clip {i}: {e}")
                results.append({'success': False, 'clip_number': i, 'error': str(e)})

        success_count = sum(1 for r in results if r.get('success'))
        logger.info(f"Pipeline complete! Created {success_count}/{len(clips)} clips")
        return results


def main():
    """CLI Entrypoint"""
    import argparse

    parser = argparse.ArgumentParser(description='Clipper: Create viral clips from YouTube videos')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--segments', default=None,
                        help='Path to existing segments.json (skips LLM analysis)')
    parser.add_argument('--aspect', default='vertical', choices=['vertical', 'square', 'horizontal'],
                        help='Output aspect ratio (default: vertical)')
    parser.add_argument('--captions', default='bold', choices=['bold', 'minimal', 'colorful', 'subtle', 'none'],
                        help='Caption preset (default: bold)')
    args = parser.parse_args()

    caption_preset = None if args.captions == 'none' else args.captions
    segments_file = Path(args.segments) if args.segments else None

    pipeline = ClipperPipeline()
    results = pipeline.process(
        youtube_url=args.url,
        aspect_ratio=args.aspect,
        caption_preset=caption_preset,
        segments_file=segments_file,
    )

    # Print results
    print(f"\n{'='*60}")
    print(f"Results: {sum(1 for r in results if r.get('success'))}/{len(results)} clips created")
    print(f"{'='*60}")
    for result in results:
        if result.get('success'):
            print(f"  Clip {result['clip_number']}: {result.get('title', '')}")
            print(f"    File: {result['output_path']}")
            print(f"    Duration: {result['duration']:.1f}s | Crop: {result['crop_method']} | Captions: {'Yes' if result['has_captions'] else 'No'}")
            print(f"    Viral score: {result.get('viral_score', 'N/A')}")
        else:
            print(f"  Clip {result['clip_number']}: FAILED - {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()