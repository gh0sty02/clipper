# Clipper

Create viral vertical clips from YouTube videos with auto-cropping and captions.

## Pipeline

1. Fetch transcript from YouTube (saved as `full_transcript.txt` + `full_transcript.srt`)
2. Use LLM to identify viral segments (outputs `segments.json`)
3. Download only the needed segments from YouTube (not the full video)
4. Auto-crop using MediaPipe face detection + add captions
5. Output clips to `outputs/`

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Options

```bash
python main.py "URL" --segments path/to/segments.json  # custom segments file
python main.py "URL" --aspect vertical                  # vertical (default), square, horizontal
python main.py "URL" --captions bold                    # bold (default), minimal, colorful, subtle, none
```

## Segments File

Clip timestamps are defined in `segments.json`. Each clip has:

```json
{
  "timestamp_start": "00:01:37,359",
  "timestamp_end": "00:01:46,078",
  "suggested_title": "Clip Title",
  "viral_score": 9.0
}
```

Clips are processed in order of highest viral score first.

## Output

```
outputs/
  full_transcript.txt        # full video transcript
  full_transcript.srt        # full video SRT
  clip_1_Clip_Title.mp4      # video clip
  clip_1_Clip_Title.srt      # clip SRT
  ...
```

## Configuration

Edit `config.py` to customize:

- **Aspect ratios**: `vertical` (9:16), `square` (1:1), `horizontal` (16:9)
- **Caption presets**: `minimal`, `bold`, `colorful`, `subtle`
- **FFmpeg settings**: encoding preset, quality (CRF), audio bitrate

## Caption Presets

| Preset | Description |
|--------|-------------|
| `bold` | Large text, lower half, single line |
| `minimal` | Small text, bottom of screen |
| `colorful` | Yellow text, centered |
| `subtle` | Small with background |
