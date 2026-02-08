import os
from google import genai
from .prompts import VIRALITY_DETECTION_PROMPT
from .formatter import format_chunk_for_prompt
import json, io, csv


def get_client():
    """Initialize OpenAI client"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return genai.Client()


def get_analysis_prompt(chunk_text, chunk_index, total_chunks):
    """Generate the analysis prompt for a chunk"""
    prompt = VIRALITY_DETECTION_PROMPT.replace("<transcript>", chunk_text)
    return prompt

def analyze_chunk(client, chunk, chunk_index, total_chunks):
    """Analyze a single chunk for viral content"""
    model = "gemini-2.5-flash-lite"
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    
    chunk_text = format_chunk_for_prompt(chunk)
    prompt = get_analysis_prompt(chunk_text, chunk_index, total_chunks)
    
    try:
        response = client.models.generate_content(
            model=model, contents=prompt
        )
        return response.text
    except Exception as e:
        return json.dumps({"clips": [], "error": str(e)})


def parse_analysis_results(raw_results):
    """Parse raw LLM JSON results into unified clip list"""
    all_clips = []
    
    for chunk_index, result in enumerate(raw_results):
        try:
            data = json.loads(result.replace("```json", "").replace("```", ""))
            clips = data.get("clips", [])
            
            for clip in clips:
                clip["chunk_index"] = chunk_index + 1
                all_clips.append(clip)
                
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse chunk {chunk_index + 1} result: {e}")
            continue
    
    return all_clips


def rank_clips(clips):
    """Rank clips by viral score"""
    return sorted(
        clips,
        key=lambda x: x.get("viral_score", 0),
        reverse=True
    )


def deduplicate_clips(clips, time_threshold_seconds=10):
    """Remove duplicate clips that overlap in time"""
    if not clips:
        return clips
    
    def timestamp_to_seconds(ts):
        parts = ts.split(":")
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s.replace(",", "."))
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s.replace(",", "."))
        return 0
    
    unique_clips = []
    
    for clip in clips:
        start = timestamp_to_seconds(clip.get("timestamp_start", "00:00:00"))
        is_duplicate = False
        
        for existing in unique_clips:
            existing_start = timestamp_to_seconds(existing.get("timestamp_start", "00:00:00"))
            
            if abs(start - existing_start) < time_threshold_seconds:
                # Keep the one with higher viral score
                if clip.get("viral_score", 0) > existing.get("viral_score", 0):
                    unique_clips.remove(existing)
                    unique_clips.append(clip)
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_clips.append(clip)
    
    return unique_clips


def format_final_results(ranked_clips, output_format="text"):
    """Format ranked clips into readable output or JSON"""
    
    if output_format == "json":
        return json.dumps({"clips": ranked_clips}, indent=2)
    
    if output_format == "csv":
        return format_as_csv(ranked_clips)
    
    if not ranked_clips:
        return "No viral-worthy moments found in the transcript."
    
    output_lines = []
    
    # Score emoji mapping
    def get_score_emoji(score):
        if score >= 8.5:
            return "🔥"
        elif score >= 7.0:
            return "⭐"
        elif score >= 5.0:
            return "💡"
        return "📌"
    
    # Content type emoji mapping
    type_emoji = {
        "educational": "📚",
        "entertainment": "🎬",
        "inspirational": "✨",
        "controversial": "🔥",
        "storytelling": "📖"
    }
    
    # Emotion emoji mapping
    emotion_emoji = {
        "curiosity": "🤔",
        "surprise": "😮",
        "humor": "😂",
        "inspiration": "💪",
        "outrage": "😡"
    }
    
    for i, clip in enumerate(ranked_clips, 1):
        score = clip.get("viral_score", 0)
        content_type = clip.get("content_type", "unknown")
        emotion = clip.get("target_emotion", "unknown")
        
        s_emoji = get_score_emoji(score)
        t_emoji = type_emoji.get(content_type, "📌")
        e_emoji = emotion_emoji.get(emotion, "💭")
        
        output_lines.append(f"\n{'='*60}")
        output_lines.append(f"{i}. {s_emoji} VIRAL SCORE: {score}/10")
        output_lines.append(f"{'='*60}")
        output_lines.append(f"📍 Timestamp: {clip.get('timestamp_start')} --> {clip.get('timestamp_end')}")
        output_lines.append(f"🎬 Title: {clip.get('suggested_title', 'N/A')}")
        output_lines.append(f"🪝 Hook: \"{clip.get('hook_text', 'N/A')}\"")
        output_lines.append(f"")
        output_lines.append(f"{t_emoji} Content Type: {content_type}")
        output_lines.append(f"{e_emoji} Target Emotion: {emotion}")
        output_lines.append(f"")
        output_lines.append(f"💡 Why it works:")
        output_lines.append(f"   {clip.get('reason', 'N/A')}")
        output_lines.append(f"")
        output_lines.append(f"🎯 Engagement Triggers: {', '.join(clip.get('engagement_triggers', []))}")
        output_lines.append(f"📱 Platforms: {', '.join(clip.get('platforms', []))}")
        output_lines.append(f"#️⃣  Hashtags: {' '.join(clip.get('hashtags', []))}")
        output_lines.append(f"📦 Found in chunk: {clip.get('chunk_index', 'N/A')}")
    
    # Summary statistics
    high_count = sum(1 for c in ranked_clips if c.get("viral_score", 0) >= 8.5)
    medium_count = sum(1 for c in ranked_clips if 7.0 <= c.get("viral_score", 0) < 8.5)
    low_count = sum(1 for c in ranked_clips if c.get("viral_score", 0) < 7.0)
    
    avg_score = sum(c.get("viral_score", 0) for c in ranked_clips) / len(ranked_clips)
    
    # Platform distribution
    platform_counts = {}
    for clip in ranked_clips:
        for platform in clip.get("platforms", []):
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
    
    # Content type distribution
    content_counts = {}
    for clip in ranked_clips:
        ct = clip.get("content_type", "unknown")
        content_counts[ct] = content_counts.get(ct, 0) + 1
    
    summary = f"""
{'='*60}
📊 ANALYSIS SUMMARY
{'='*60}

Total clips found: {len(ranked_clips)}
Average viral score: {avg_score:.1f}/10

Score Distribution:
  🔥 High (8.5+): {high_count}
  ⭐ Medium (7.0-8.4): {medium_count}
  💡 Moderate (5.0-6.9): {low_count}

Platform Recommendations:
{chr(10).join(f'  📱 {platform}: {count} clips' for platform, count in sorted(platform_counts.items(), key=lambda x: x[1], reverse=True))}

Content Types:
{chr(10).join(f'  {type_emoji.get(ct, "📌")} {ct}: {count} clips' for ct, count in sorted(content_counts.items(), key=lambda x: x[1], reverse=True))}

{'='*60}
📋 DETAILED RESULTS
{'='*60}
"""
    
    return summary + "\n".join(output_lines)


def consolidate_results(raw_results, output_format="text"):
    """Consolidate and rank results from all chunks"""
    clips = parse_analysis_results(raw_results)
    deduplicated_clips = deduplicate_clips(clips)
    ranked_clips = rank_clips(deduplicated_clips)
    return format_final_results(ranked_clips, output_format)


def analyze_for_viral_content(chunks, verbose=True, output_format="text"):
    """
    Main function to analyze all chunks for viral content.
    
    Args:
        chunks: List of subtitle chunks
        verbose: Print progress updates
        output_format: "text" for formatted output, "json" for raw JSON
    
    Returns:
        Formatted string with ranked viral moments
    """
    client = get_client()
    total_chunks = len(chunks)
    raw_results = []
    
    for i, chunk in enumerate(chunks, 1):
        if verbose:
            print(f"  Analyzing chunk {i}/{total_chunks}...")
        
        result = analyze_chunk(client, chunk, i, total_chunks)
        print(result)
        raw_results.append(result)
        
        if verbose:
            try:
                data = json.loads(result.replace("```json", "").replace("```", ""))
                clip_count = len(data.get("clips", []))
                if clip_count == 0:
                    print(f"    No viral moments in this chunk")
                else:
                    print(f"    Found {clip_count} potential clip(s)")
            except json.JSONDecodeError:
                print(f"    Warning: Invalid JSON response")
        
    if verbose:
        print("  Consolidating and ranking results...")
    
    return consolidate_results(raw_results, output_format)


def get_clips_as_json(chunks, verbose=True):
    """
    Convenience function to get results as parsed JSON.
    
    Args:
        chunks: List of subtitle chunks
        verbose: Print progress updates
    
    Returns:
        Dictionary with clips list
    """
    result = analyze_for_viral_content(chunks, verbose, output_format="json")
    return json.loads(result.replace("```json", "").replace("```", ""))

def format_as_csv(clips):
    """Format clips as CSV string"""
    if not clips:
        return "No viral-worthy moments found in the transcript."
    
    # Define CSV columns
    fieldnames = [
        "id",
        "viral_score",
        "timestamp_start",
        "timestamp_end",
        "suggested_title",
        "hook_text",
        "reason",
        "content_type",
        "target_emotion",
        "engagement_triggers",
        "platforms",
        "hashtags",
        "chunk_index"
    ]
    
    # Write to string buffer
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore', lineterminator='\n')
    
    writer.writeheader()
    
    for i, clip in enumerate(clips, 1):
        row = {
            "id": i,
            "viral_score": clip.get("viral_score", 0),
            "timestamp_start": clip.get("timestamp_start", ""),
            "timestamp_end": clip.get("timestamp_end", ""),
            "suggested_title": clip.get("suggested_title", ""),
            "hook_text": clip.get("hook_text", ""),
            "reason": clip.get("reason", ""),
            "content_type": clip.get("content_type", ""),
            "target_emotion": clip.get("target_emotion", ""),
            "engagement_triggers": "|".join(clip.get("engagement_triggers", [])),
            "platforms": "|".join(clip.get("platforms", [])),
            "hashtags": " ".join(clip.get("hashtags", [])),
            "chunk_index": clip.get("chunk_index", "")
        }
        writer.writerow(row)
    
    return output.getvalue()