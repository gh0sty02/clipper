import argparse
from transcript_parser.parser import parse_srt
from transcript_parser.chunker import chunk_subtitles
from llm.formatter import format_chunk_for_prompt
from llm.analyzer import analyze_for_viral_content

def main():
    parser = argparse.ArgumentParser(
        description="Analyze SRT transcripts for viral content"
    )
    
    parser.add_argument(
        "srt_file",
        help="Path to the SRT file"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Max duration per chunk in seconds (preferred over segments)"
    )
    parser.add_argument(
        "--segments",
        type=int,
        default=25,
        help="Max segments per chunk (default: 25)"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=10,
        help="Overlap between chunks in seconds (default: 10)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "csv"],
        default="text",
        help="Output format: text, json, or csv (default: text)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: print to console)"
    )
    
    args = parser.parse_args()
    
    # Parse SRT file
    print(f"Parsing SRT file: {args.srt_file}")
    subtitles = parse_srt(args.srt_file)
    print(f"Found {len(subtitles)} subtitle segments")
    
    # Chunk subtitles
    chunks = chunk_subtitles(
        subtitles,
        max_duration_seconds=args.duration,
        max_segments=args.segments,
        overlap_seconds=args.overlap
    )
    print(f"Created {len(chunks)} chunks")
    
    # Display chunk info
    for i, chunk in enumerate(chunks):
        start_time = chunk[0]['start_seconds']
        end_time = chunk[-1]['end_seconds']
        print(f"  Chunk {i + 1}: {len(chunk)} segments ({start_time:.1f}s - {end_time:.1f}s)")
    
    # # Analyze for viral content
    print("\nAnalyzing for viral content...")
    results = analyze_for_viral_content(chunks, output_format=args.format)
    
    # Output results
    if args.output:
        with open(args.output, 'a', encoding='utf-8') as f:
            f.write(results)
        print(f"\nResults saved to: {args.output}")
    else:
        print("\n" + "=" * 50)
        print("VIRAL CONTENT CANDIDATES")
        print("=" * 50)
        print(results)


if __name__ == "__main__":
    main()