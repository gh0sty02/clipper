from .timestamp import parse_timestamp, get_end_timestamp

def chunk_subtitles(subtitles, max_duration_seconds=None, max_segments=None, overlap_seconds=5):
    """
    Chunk subtitles based on duration (preferred) or segment count.
    
    Args:
        subtitles: List of subtitle dicts with 'index', 'timestamp', 'text'
        max_duration_seconds: Max duration per chunk in seconds (preferred if provided)
        max_segments: Max number of segments per chunk (fallback)
        overlap_seconds: Overlap duration between chunks in seconds
    
    Returns:
        List of chunks, each containing subtitle entries
    """
    
    if not subtitles:
        return []
    
    # Prefer seconds-based chunking
    if max_duration_seconds is not None:
        return _chunk_by_duration(subtitles, max_duration_seconds, overlap_seconds)
    elif max_segments is not None:
        return _chunk_by_segments(subtitles, max_segments, overlap_seconds)
    else:
        raise ValueError("Must provide either max_duration_seconds or max_segments")

def _chunk_by_duration(subtitles, max_duration_seconds, overlap_seconds):
    """Chunk based on time duration with overlap"""
    chunks = []
    i = 0
    
    while i < len(subtitles):
        chunk_start_time = parse_timestamp(subtitles[i]['timestamp'])
        chunk = []
        
        j = i
        while j < len(subtitles):
            current_time = parse_timestamp(subtitles[j]['timestamp'])
            
            if current_time - chunk_start_time >= max_duration_seconds:
                break
            
            chunk.append({
                **subtitles[j],
                'start_seconds': parse_timestamp(subtitles[j]['timestamp']),
                'end_seconds': get_end_timestamp(subtitles[j]['timestamp'])
            })
            j += 1
        
        if chunk:
            chunks.append(chunk)
        
        # Find next starting position considering overlap
        if j >= len(subtitles):
            break
            
        # Move back to include overlap
        overlap_start_time = parse_timestamp(subtitles[j]['timestamp']) - overlap_seconds
        i = j
        
        # Find the first subtitle that starts at or after overlap_start_time
        while i > 0 and parse_timestamp(subtitles[i]['timestamp']) > overlap_start_time:
            i -= 1
        
        # Ensure we make progress
        if i <= chunks[-1][0].get('original_index', 0) if chunks else False:
            i = j
    
    return chunks

def _chunk_by_segments(subtitles, max_segments, overlap_seconds):
    """Chunk based on segment count with time-based overlap"""
    chunks = []
    i = 0
    
    while i < len(subtitles):
        chunk_end = min(i + max_segments, len(subtitles))
        chunk = []
        
        for j in range(i, chunk_end):
            chunk.append({
                **subtitles[j],
                'start_seconds': parse_timestamp(subtitles[j]['timestamp']),
                'end_seconds': get_end_timestamp(subtitles[j]['timestamp'])
            })
        
        chunks.append(chunk)
        
        if chunk_end >= len(subtitles):
            break
        
        # Calculate overlap based on seconds
        overlap_start_time = get_end_timestamp(subtitles[chunk_end - 1]['timestamp']) - overlap_seconds
        
        # Find new starting position
        new_i = chunk_end
        for k in range(chunk_end - 1, i - 1, -1):
            if parse_timestamp(subtitles[k]['timestamp']) >= overlap_start_time:
                new_i = k
            else:
                break
        
        # Ensure progress
        i = new_i if new_i > i else chunk_end
    
    return chunks