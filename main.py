import sys
from pathlib import Path
import logging
from config import TEMP_DIR, OUTPUT_DIR
from utils.video_downloader import VideoDownloader
from utils.transcript_fetcher import TranscriptFetcher
from utils.crop_detector import CropDetector
from utils.video_processor import VideoProcessor
from utils.caption_generator import CaptionGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClipperPipeline:
    """Complete pipeline for creating clips from YouTube videos"""
    
    def __init__(self):
        self.downloader = VideoDownloader(TEMP_DIR)
        self.transcript_fetcher = TranscriptFetcher()
        self.video_processor = VideoProcessor()
    
    def process_video(
        self,
        youtube_url: str = None,
        clips: list = [],
        output_dir: Path = OUTPUT_DIR,
        aspect_ratio: str = 'vertical',
        caption_preset: str = None,
        local_file: str = None
    ) -> list:
        """
        Complete pipeline: download, process, and create clips
        
        Args:
            youtube_url: YouTube video URL
            clips: List of dicts with 'start_time' and 'end_time'
            output_dir: Directory for output clips
            aspect_ratio: 'vertical', 'square', or 'horizontal'
            caption_preset: Optional caption style ('minimal', 'bold', etc.)
            local_file: Optional path to local video file
            
        Returns:
            List of created clip info dicts
        """
        
        if local_file:
            logger.info(f"Starting pipeline for local file: {local_file}")
            video_path = local_file
        else:
            logger.info(f"Starting pipeline for: {youtube_url}")
            
            # Step 1: Download video
            logger.info("Step 1: Downloading video...")
            video_info = self.downloader.download(youtube_url)
            video_path = video_info['path']
        
        # Step 2: Fetch transcript (if captions needed and not local file)
        transcript_data = None
        if caption_preset and not local_file:
            logger.info("Step 2: Fetching transcript...")
            try:
                transcript_data = self.transcript_fetcher.fetch_transcript(youtube_url)
            except Exception as e:
                logger.warning(f"Could not fetch transcript: {e}")
                logger.warning("Proceeding without captions")
                caption_preset = None
        elif local_file and caption_preset:
            logger.warning("Captions are not yet supported for local files (need transcript source). Skipping captions.")
            caption_preset = None
        
        # Step 3: Process each clip
        logger.info(f"Step 3: Processing {len(clips)} clips...")
        results = []
        
        for i, clip in enumerate(clips, 1):
            clip_name = f"clip_{i}_{clip['start_time']}_{clip['end_time']}.mp4"
            output_path = output_dir / clip_name
            
            logger.info(f"Processing clip {i}/{len(clips)}: {clip['start_time']}s - {clip['end_time']}s")
            
            # Generate subtitles if needed
            subtitle_file = None
            if caption_preset and transcript_data:
                # Filter transcript for this clip's time range (deep copy to avoid mutation)
                clip_transcript = [
                    {
                        'text': seg['text'],
                        'start': seg['start'] - clip['start_time'],
                        'duration': seg['duration']
                    }
                    for seg in transcript_data
                    if clip['start_time'] <= seg['start'] <= clip['end_time']
                ]
                
                if clip_transcript:
                    caption_gen = CaptionGenerator(preset=caption_preset)
                    subtitle_file = TEMP_DIR / f"clip_{i}.ass"
                    caption_gen.generate_ass_file(clip_transcript, subtitle_file)

                    # Save SRT file to output directory
                    srt_filename = f"clip_{i}_{clip['start_time']}_{clip['end_time']}.srt"
                    srt_path = output_dir / srt_filename
                    self.transcript_fetcher.save_srt(clip_transcript, str(srt_path))
            
            # Process video
            try:
                result = self.video_processor.create_clip(
                    input_path=video_path,
                    output_path=str(output_path),
                    start_time=clip['start_time'],
                    end_time=clip['end_time'],
                    aspect_ratio=aspect_ratio,
                    crop_method='auto',
                    subtitle_file=str(subtitle_file) if subtitle_file else None
                )
                
                results.append({
                    **result,
                    'clip_number': i,
                    'has_captions': subtitle_file is not None
                })
                
            except Exception as e:
                logger.error(f"Failed to process clip {i}: {e}")
                results.append({
                    'success': False,
                    'clip_number': i,
                    'error': str(e)
                })
        
        logger.info(f"Pipeline complete! Created {sum(1 for r in results if r['success'])} clips")
        
        return results


def main():
    """CLI Entrypoint"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clipper: Create viral clips from videos')
    parser.add_argument('url', nargs='?', help='YouTube URL (optional). If not provided, uses input.mp4')
    args = parser.parse_args()

    pipeline = ClipperPipeline()
    
    # Define clips to extract (Hardcoded for now as per previous example)
    clips = [
        {'start_time': 10, 'end_time': 30},   # 20-second clip
        {'start_time': 60, 'end_time': 90},   # 30-second clip
        {'start_time': 180, 'end_time': 240}, # 60-second clip
    ]
    
    if args.url:
        print(f"URL provided: {args.url}")
        results = pipeline.process_video(
            youtube_url=args.url,
            clips=clips,
            aspect_ratio='vertical',
            caption_preset='bold'
        )
    else:
        if not Path("input.mp4").exists():
            logger.error("No URL provided and 'input.mp4' not found in current directory.")
            sys.exit(1)
            
        print("No URL provided. Using local 'input.mp4'.")
        results = pipeline.process_video(
            local_file="input.mp4",
            clips=clips,
            aspect_ratio='vertical',
            caption_preset='bold'
        )
    
    # Print results
    for result in results:
        if result['success']:
            print(f"✓ Clip {result['clip_number']}: {result['output_path']}")
            print(f"  Duration: {result['duration']}s")
            print(f"  Crop method: {result['crop_method']}")
            print(f"  Captions: {'Yes' if result['has_captions'] else 'No'}")
        else:
            print(f"✗ Clip {result['clip_number']}: Failed - {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()