import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi
import inspect

print("Module file:", youtube_transcript_api.__file__)
print("Class attributes:", dir(YouTubeTranscriptApi))

try:
    print("list_transcripts exists:", hasattr(YouTubeTranscriptApi, 'list_transcripts'))
except:
    print("list_transcripts check failed")

try:
    print("get_transcript exists:", hasattr(YouTubeTranscriptApi, 'get_transcript'))
except:
    print("get_transcript check failed")
