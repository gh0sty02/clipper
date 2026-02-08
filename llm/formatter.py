def format_chunk_for_prompt(chunk):
    """Format a chunk for LLM prompt"""
    lines = []
    for sub in chunk:
        lines.append(f"[{sub['timestamp']}] {sub['text']}")
    return '\n'.join(lines)