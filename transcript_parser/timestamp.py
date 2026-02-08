import re

def parse_timestamp(timestamp):
    """Convert SRT timestamp to seconds"""
    # Format: 00:01:23,456 --> 00:01:25,789
    start_time = timestamp.split(' --> ')[0]
    h, m, s = start_time.replace(',', '.').split(':')
    return float(h) * 3600 + float(m) * 60 + float(s)

def get_end_timestamp(timestamp):
    """Get end time in seconds from SRT timestamp"""
    end_time = timestamp.split(' --> ')[1]
    h, m, s = end_time.replace(',', '.').split(':')
    return float(h) * 3600 + float(m) * 60 + float(s)