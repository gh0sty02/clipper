import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Directories
BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "outputs"

# Create directories if they don't exist
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Video settings
ASPECT_RATIOS = {
    'vertical': (9, 16),      # Instagram Reels, TikTok, YouTube Shorts
    'square': (1, 1),         # Instagram Post
    'horizontal': (16, 9)     # YouTube
}

OUTPUT_RESOLUTIONS = {
    'vertical': (1080, 1920),
    'square': (1080, 1080),
    'horizontal': (1920, 1080)
}

# FFmpeg settings
FFMPEG_PRESET = 'fast'
FFMPEG_CRF = 23
AUDIO_BITRATE = '128k'

# Crop detection settings
CROP_DETECT_LIMIT = 24
CROP_DETECT_ROUND = 16

# Face detection settings
FACE_DETECTION_ENABLED = True
FACE_CASCADE_PATH = 'haarcascade_frontalface_default.xml'

# Caption presets
CAPTION_PRESETS = {
    'minimal': {
        'font': 'Arial',
        'size': 24,
        'color': '&HFFFFFF&',
        'outline': 2,
        'position': 'bottom'
    },
    'bold': {
        'font': 'Arial Black',
        'size': 42,
        'color': '&HFFFFFF&',
        'outline': 3,
        'shadow': 0,
        'position': 'lower',
        'margin_v': 280,
        'max_words': 4
    },
    'colorful': {
        'font': 'Arial-Bold',
        'size': 36,
        'color': '&H00FFFF&',  # Yellow
        'outline': 3,
        'position': 'center'
    },
    'subtle': {
        'font': 'Arial',
        'size': 20,
        'color': '&HFFFFFF&',
        'outline': 1,
        'background': True,
        'position': 'bottom'
    }
}