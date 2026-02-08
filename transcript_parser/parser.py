import re

def parse_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by double newline (separates subtitle blocks)
    blocks = re.split(r'\n\n+', content.strip())
    
    subtitles = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            index = lines[0]
            timestamp = lines[1]
            text = ' '.join(lines[2:])
            subtitles.append({
                'index': index,
                'timestamp': timestamp,
                'text': text
            })
    
    return subtitles