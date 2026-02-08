# Clipper - Viral Content Detection Tool

## Overview

**clip_finder.py** is a Python tool that analyzes video transcripts (in SRT format) to automatically identify viral-worthy moments using AI-powered content analysis. It breaks down transcripts into manageable chunks and uses Google's Gemini LLM to detect and rank clips with high viral potential.

## What It Does

1. **Parses SRT Files**: Reads video transcript SRT files with timing information
2. **Chunks Transcripts**: Splits the transcript into overlapping chunks for comprehensive analysis
3. **AI Analysis**: Uses Google Gemini 2.5 Flash Lite to analyze each chunk for viral content patterns
4. **Scores & Ranks**: Generates viral scores (0-10) and ranks clips by their viral potential
5. **Smart Deduplication**: Removes duplicate clips with similar timestamps
6. **Multi-format Output**: Generates results in text, JSON, or CSV format

## Usage

### Basic Usage

```bash
python clip_finder.py <path_to_srt_file>
```

### Command-Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `srt_file` | string | Required | Path to the SRT transcript file |
| `--duration` | int | None | Max duration per chunk in seconds (takes priority over segments) |
| `--segments` | int | 25 | Max number of subtitle segments per chunk |
| `--overlap` | int | 10 | Overlap between chunks in seconds (for context continuity) |
| `--format` | string | text | Output format: `text`, `json`, or `csv` |
| `--output` | string | None | Output file path (if not specified, prints to console) |

### Examples

#### Example 1: Basic Analysis (Display to Console)
```bash
python clip_finder.py transcript.srt
```

#### Example 2: Time-based Chunking (60 seconds per chunk)
```bash
python clip_finder.py transcript.srt --duration 60
```

#### Example 3: CSV Output with Append Mode
```bash
python clip_finder.py transcript.srt --format csv --output clips.csv
```
*Note: Multiple runs will append results to the CSV file*

#### Example 4: JSON Output with Custom Overlap
```bash
python clip_finder.py transcript.srt --segments 20 --overlap 5 --format json --output results.json
```

## Output Formats

### Text Format (Default)
Produces a human-readable report with:
- Summary statistics (total clips, average viral score, score distribution)
- Platform recommendations
- Content type breakdown
- Detailed clips with hooks, engagement triggers, and hashtags

### JSON Format
Raw JSON structure containing:
```json
{
  "clips": [
    {
      "viral_score": 8.5,
      "timestamp_start": "00:01:30",
      "timestamp_end": "00:02:45",
      "suggested_title": "...",
      "hook_text": "...",
      "content_type": "entertainment",
      "target_emotion": "humor",
      "platforms": ["TikTok", "YouTube Shorts"],
      ...
    }
  ]
}
```

### CSV Format
Tabular format with columns:
- ID, Viral Score, Start/End Timestamps
- Title, Hook Text, Reason
- Content Type, Target Emotion
- Engagement Triggers, Platforms, Hashtags
- Chunk Index

## Key Features

### Chunk Analysis Strategy
- Splits transcript into overlapping chunks to catch context
- Configurable segment count and duration
- Overlap ensures important moments aren't missed at chunk boundaries

### Viral Content Detection
Identifies clips based on:
- **Engagement Triggers**: Curiosity gaps, emotional hooks, humor, surprises
- **Content Types**: Educational, entertainment, inspirational, controversial, storytelling
- **Target Emotions**: Curiosity, surprise, humor, inspiration, outrage
- **Platform Fit**: Optimized suggestions for TikTok, YouTube Shorts, Instagram Reels, etc.

### Deduplication
Automatically removes similar clips within a 10-second time threshold, keeping the highest-scored variant

## Requirements

- Python 3.x
- Google Gemini API key (set in `GEMINI_API_KEY` environment variable)
- Dependencies: `google-genai`, and internal modules (transcript_parser, llm)

## Environment Setup

```bash
export GEMINI_API_KEY=your_api_key_here
```

## Output Examples

### Console Output
```
Parsing SRT file: transcript.srt
Found 500 subtitle segments
Created 10 chunks

Chunk 1: 25 segments (0.0s - 45.2s)
Chunk 2: 25 segments (35.2s - 80.4s)
...

Analyzing for viral content...
Consolidating and ranking results...

============================================================
📊 ANALYSIS SUMMARY
============================================================

Total clips found: 15
Average viral score: 7.8/10
...
```

### CSV Output File
```csv
id,viral_score,timestamp_start,timestamp_end,suggested_title,hook_text,...
1,8.5,00:01:30,00:02:45,"Mind-Blowing Fact","Did you know that...",
2,7.9,00:05:00,00:06:15,"Unexpected Twist","But then something happened...",
...
```

## Tips for Best Results

1. **Use Time-based Chunking**: For videos with consistent talking pace, use `--duration` instead of segment count
2. **Adjust Overlap**: Increase overlap (15-20s) for videos with subtle moments; decrease (5s) for obvious clips
3. **Append Mode**: Use `--format csv --output clips.csv` to accumulate results from multiple video analyses
4. **Review JSON First**: Use JSON format to inspect structured data before processing further
5. **Platform-Specific Analysis**: Different platforms favor different content types (TikTok = entertainment/humor, LinkedIn = educational/inspirational)

## Performance Notes

- Analysis time depends on transcript length and LLM API response time
- Each chunk is analyzed sequentially for reliability
- Results are deduplicated and ranked by viral potential

---

**Clipper v1.0** - Powered by Google Gemini API
