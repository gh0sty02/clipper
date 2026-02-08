import json
import logging
import os
from pathlib import Path
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT =VIRAL_CLIP_PROMPT = """You are an expert viral content strategist and video editor specializing in short-form content optimization.

Given a full video transcript with timestamps, identify the most viral-worthy segments that would perform exceptionally well as short-form vertical content (TikTok, Instagram Reels, YouTube Shorts).

CRITICAL DURATION REQUIREMENTS:
- MINIMUM clip duration: 25 seconds (absolutely no shorter)
- MAXIMUM clip duration: 90 seconds (1.5 minutes)
- OPTIMAL range: 35-60 seconds (sweet spot for engagement)
- Reject any segment that cannot meet the 25-second minimum

NATURAL ENDING REQUIREMENTS:
- MUST end on complete thoughts, sentences, or natural pauses
- NEVER cut mid-sentence or mid-word
- Look for natural conversation boundaries:
  * Full stop/period in dialogue
  * Question completion followed by answer
  * Punchline delivery completion
  * Story arc resolution (even if mini)
  * Emotional beat conclusion
  * Laughter/applause moments
- If a great moment is too short, EXTEND the end timestamp to include the complete thought/reaction

CONTENT SELECTION CRITERIA (prioritize in order):
1. **Strong Opening Hook** - First 2-3 seconds must grab attention
   - Controversial statement
   - Surprising fact
   - Bold question
   - Shocking claim
   - Relatable problem statement

2. **Emotional Journey** - Segment should have a clear emotional arc
   - Build-up and payoff
   - Problem and insight
   - Setup and punchline
   - Tension and resolution

3. **Standalone Value** - Can be understood without full context
   - Self-contained story or point
   - Complete thought or argument
   - Doesn't require prior knowledge

4. **Viral Triggers** (look for):
   - Quotable one-liners (shareable text overlays)
   - "Wait, what?" moments (pattern interrupts)
   - Controversial takes (sparks debate)
   - Actionable advice (save-worthy)
   - Relatable struggles (comment-worthy)
   - Unexpected reveals (rewatch-worthy)
   - Humor/wit (share-worthy)

QUALITY OVER QUANTITY:
- Return 8-15 clips maximum (be selective, not exhaustive)
- Only include segments scoring 7.0 or higher
- Better to have 10 great clips than 25 mediocre ones
- Avoid redundant clips covering the same point

TIMESTAMP PRECISION:
- Use EXACT timestamps from the provided transcript
- Format: SRT standard (HH:MM:SS,mmm)
- Double-check that end timestamp creates a complete, natural conclusion
- Verify duration is between 25-90 seconds

VIRAL SCORING RUBRIC (be realistic):
- 9.5-10.0: Exceptional - guaranteed viral potential, multiple triggers
- 8.5-9.4: Excellent - very high viral probability, strong hook + payoff
- 7.5-8.4: Strong - good viral potential, at least 2 engagement triggers
- 7.0-7.4: Solid - decent potential, needs one strong element
- Below 7.0: DO NOT INCLUDE

Return ONLY valid JSON in this exact format (no markdown, no extra text):

{
  "clips": [
    {
      "id": 1,
      "timestamp_start": "00:01:37,359",
      "timestamp_end": "00:02:15,840",
      "duration_seconds": 38,
      "suggested_title": "Short Catchy Title (max 60 chars)",
      "hook_text": "The exact opening line that grabs attention",
      "closing_context": "How the segment naturally concludes",
      "reason": "Detailed explanation of why this will go viral - be specific about the hook, emotional journey, and payoff",
      "engagement_triggers": ["hook", "quotable", "controversial", "relatable"],
      "viral_score": 8.7,
      "platforms": ["tiktok", "reels", "shorts"],
      "hashtags": ["#relevanthash", "#trending", "#niche"],
      "content_type": "educational",
      "target_emotion": "curiosity",
      "standalone_context": "Brief context if viewer needs any background",
      "chunk_index": 1
    }
  ],
  "metadata": {
    "total_clips_found": 12,
    "average_viral_score": 8.2,
    "video_analysis": "Brief overview of the content themes and why these segments were chosen"
  }
}

ENGAGEMENT TRIGGER DEFINITIONS:
- "hook": Opens with attention-grabbing statement/question
- "quotable": Contains shareable one-liner or memorable phrase
- "controversial": Challenges common beliefs or sparks debate
- "relatable": Addresses common experience/struggle
- "educational": Teaches valuable insight or skill
- "emotional": Evokes strong feeling (inspiration, anger, joy)
- "shock": Surprising or unexpected information
- "humor": Genuinely funny or witty
- "storytelling": Compelling narrative arc
- "actionable": Provides clear takeaway or next step

CONTENT TYPE OPTIONS:
- educational: Teaching or explaining something
- entertainment: Primarily for enjoyment/humor
- motivational: Inspirational or empowering
- controversial: Debate-sparking hot take
- storytelling: Narrative-driven
- how-to: Instructional/tutorial
- reaction: Response or commentary

TARGET EMOTION OPTIONS:
- curiosity: Makes viewer want to learn more
- surprise: Unexpected revelation
- inspiration: Motivates or empowers
- validation: Confirms viewer's beliefs/experiences
- outrage: Sparks disagreement (engagement)
- joy: Makes viewer happy/laugh
- fascination: Deeply interesting
- relief: Solves a problem

EXAMPLE OF GOOD VS BAD CLIP SELECTION:

❌ BAD (8 seconds, cuts mid-sentence):
Start: "So I think the problem with social media is—"
End: "—that people don't realize how much time"
Problem: Too short, incomplete thought, no payoff

✅ GOOD (42 seconds, complete thought):
Start: "So I think the problem with social media is that people don't realize how much time they're actually wasting."
Middle: [Continues with explanation and example]
End: "And that's why I deleted Instagram for 30 days, and honestly, it changed my life."
Why: Complete arc, relatable problem, surprising solution, actionable insight

Remember: You're not just extracting moments—you're crafting standalone micro-content pieces that can succeed independently. Each clip should feel like a complete, satisfying experience."""


class SegmentAnalyzer:
    """Use OpenRouter LLM to identify viral segments from a transcript"""

    def __init__(self):
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment. Set it in .env file.")
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

    def analyze(self, srt_content: str, model: str = "openai/gpt-oss-120b:free") -> dict:
        """
        Send transcript to LLM via OpenRouter and get viral segment timestamps back.

        Args:
            srt_content: Full transcript in SRT format
            model: OpenRouter model to use

        Returns:
            Dict with 'clips' list matching segments.json format
        """
        logger.info(f"Analyzing transcript with {model}...")

        user_prompt = (
            "Here is the full video transcript in SRT format. "
            "Analyze it and identify the most viral-worthy segments.\n\n"
            f"```srt\n{srt_content}\n```"
        )

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )

        # Extract JSON from response
        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split('\n')
            raw = '\n'.join(lines[1:-1])

        segments = json.loads(raw)

        clip_count = len(segments.get('clips', []))
        logger.info(f"LLM identified {clip_count} viral segments")

        return segments

    def analyze_and_save(self, srt_content: str, output_path: Path,
                         model: str = "google/gemini-2.0-flash-001") -> Path:
        """
        Analyze transcript and save segments.json

        Args:
            srt_content: Full transcript in SRT format
            output_path: Path to save segments.json
            model: OpenRouter model to use

        Returns:
            Path to saved segments.json
        """
        segments = self.analyze(srt_content, model=model)

        output_path = Path(output_path)
        output_path.write_text(json.dumps(segments, indent=2), encoding='utf-8')
        logger.info(f"Saved segments to: {output_path}")

        return output_path
