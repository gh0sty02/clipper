# Clipper

Create vertical clips from YouTube videos or local files with auto-cropping and captions.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### From YouTube URL

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### From Local File

Place an `input.mp4` file in the project directory and run:

```bash
python main.py
```

## Output

Clips are saved to the `outputs/` directory with the naming format:
```
clip_1_10_30.mp4  (clip 1, from 10s to 30s)
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

## Notes

- Captions are auto-fetched from YouTube transcripts
- Local files do not support auto-captions (no transcript source)
- Clips are defined in `main.py` (edit the `clips` list to change time ranges)
