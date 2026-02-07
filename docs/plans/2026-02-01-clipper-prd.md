# Clipper - Product Requirements Document

**Version:** 1.0
**Date:** 2026-02-01
**Status:** Draft

---

## 1. Overview

### 1.1 Problem Statement

Content creators, podcasters, and social media managers spend significant time manually identifying and extracting viral-worthy moments from long-form content. The process of finding the right clips, trimming them, and adding captions is tedious and time-consuming.

### 1.2 Solution

Clipper is a web application that automatically analyzes long-form YouTube content and extracts high-potential short-form clips optimized for platforms like YouTube Shorts, Instagram Reels, and TikTok.

### 1.3 Core Value Proposition

- **Save time:** Automated clip identification vs. manual scrubbing through hours of content
- **Improve quality:** AI-powered selection based on viral patterns and current trends
- **Ready to publish:** Clips come with optional burned-in captions in proven short-form styles

---

## 2. User Flow

1. User logs in via Google OAuth
2. User pastes a YouTube video URL
3. System fetches and processes the video transcript
4. AI analyzes transcript to identify high-potential segments based on:
   - Trending topics/keywords
   - Emotional hooks (controversy, humor, insights)
   - Natural narrative arcs (complete thoughts, punchlines)
5. System returns clips above a confidence threshold (capped at 10-15 clips)
6. User previews clips in-browser with:
   - Timestamp markers on a timeline
   - Virality score indicators
   - Reasoning for why each clip was selected
7. User selects clips to export and chooses:
   - Raw or captioned version
   - Caption style preset (if captioned)
8. System processes video: trims segments, optionally burns in captions
9. User downloads clips

---

## 3. Functional Requirements

### 3.1 Input Sources

| Requirement | Details |
|-------------|---------|
| Supported platforms | YouTube only (MVP) |
| Input method | YouTube URL paste |
| Video length limits | Tiered by plan (free: 30 min, paid: up to 3 hours) |

### 3.2 Clip Generation

| Requirement | Details |
|-------------|---------|
| Clip duration | 15-90 seconds |
| Clip boundaries | Natural content boundaries (complete thoughts, not arbitrary cuts) |
| Clips per video | Threshold-based selection, capped at 10-15 clips |
| Selection criteria | Virality score above confidence threshold |

### 3.3 Output Options

| Requirement | Details |
|-------------|---------|
| Raw clips | Trimmed video segment, no modifications |
| Captioned clips | Auto-generated captions burned into video |
| Caption presets | 3-4 style presets (minimal, bold, colorful, etc.) |
| Default output | Captioned version (user can choose raw) |

### 3.4 Authentication

| Requirement | Details |
|-------------|---------|
| Login required | Yes, required to use the product |
| Auth method | Google OAuth only |
| Account data | Email, name, avatar from Google profile |

### 3.5 Storage & Retention

| Requirement | Details |
|-------------|---------|
| Default retention | 7 days |
| Persistent storage | Future paid feature |
| User deletion | Users can delete clips anytime |

---

## 4. AI/ML Component

### 4.1 Approach

**Decision Required:** The viral prediction model approach needs further research.

#### Options:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **1. LLM with prompting** | Use GPT-4/Claude with crafted prompts including trending topics and engagement patterns | Fast to ship, easy to iterate, no training needed | Dependent on prompt quality, may be less accurate |
| **2. Fine-tuned LLM** | Fine-tune base model on labeled viral vs. non-viral clips | Better accuracy for specific use case | Needs labeled dataset, more expensive |
| **3. Custom ML classifier** | Train model from scratch on features like keyword density, sentiment, topic relevance | Full control, potentially most accurate | Significant ML engineering effort |

**Recommendation:** Start with Option 1 (LLM with prompting) for MVP. Iterate on prompts, validate product-market fit, then consider fine-tuning based on real user data.

### 4.2 Viral Prediction Criteria

The model should evaluate clips based on:

- **Trending relevance:** Does the content touch on currently trending topics?
- **Emotional hooks:** Controversy, humor, surprising facts, hot takes
- **Narrative completeness:** Does the clip tell a complete micro-story?
- **Quote potential:** Memorable, shareable statements
- **Visual/audio cues:** From transcript - laughter, applause, exclamations (if detectable)

### 4.3 Trending Data Sources

#### Recommended for MVP (Free):

1. **Google Trends (pytrends)** - Unofficial Python library, free but rate-limited
2. **YouTube Trending** - YouTube Data API for trending videos in relevant categories

#### Future Upgrades (Paid):

| Source | Cost | Use Case |
|--------|------|----------|
| SerpApi (Google Trends) | ~$50-75/mo | Reliable Google Trends access |
| Exploding Topics | ~$99/mo+ | Emerging trends before they peak |
| Reddit API | Free | Niche trend detection |
| Listen Notes API | Varies | Podcast-specific trends |

#### Implementation Notes:

- Cache trending data aggressively (refresh every few hours, not per-request)
- LLM can also use "evergreen viral patterns" from training data
- Trending context is injected into LLM prompt alongside transcript

---

## 5. Technical Architecture

### 5.1 High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Next.js App   │────▶│   Python API    │────▶│  Job Queue      │
│   (Vercel)      │     │   (Railway)     │     │  (Redis/Celery) │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        │                                │                                │
                        ▼                                ▼                                ▼
               ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
               │  Transcript     │              │  LLM Analysis   │              │  Video          │
               │  Fetching       │              │  (Clip Select)  │              │  Processing     │
               │                 │              │                 │              │  (FFmpeg)       │
               └─────────────────┘              └─────────────────┘              └─────────────────┘
```

### 5.2 Tech Stack

| Layer | Technology | Hosting |
|-------|------------|---------|
| Frontend | Next.js | Vercel |
| Backend | Python (FastAPI/Flask) | Railway |
| Job Queue | Redis + Celery | Railway |
| Database | PostgreSQL | Railway |
| Object Storage | Cloudflare R2 or AWS S3 | - |
| Video Processing | FFmpeg | Railway (workers) |
| Transcription | youtube-transcript-api, Whisper (fallback) | - |
| LLM | OpenAI or Anthropic API (TBD) | - |

### 5.3 Processing Pipeline

```
1. Job Created
   └─▶ Status: pending

2. Fetch Transcript
   ├─▶ Try youtube-transcript-api
   ├─▶ Fallback: download audio → Whisper
   └─▶ Status: transcribing

3. Analyze Transcript
   ├─▶ Fetch current trending data (cached)
   ├─▶ Send to LLM with prompt + trending context
   ├─▶ Receive clip recommendations with scores
   └─▶ Status: analyzing

4. Create Clip Records
   ├─▶ Store clip metadata (timestamps, scores, reasons)
   └─▶ Status: completed (clips pending processing)

5. Process Individual Clips (on-demand when user exports)
   ├─▶ Download source video if not cached (yt-dlp)
   ├─▶ Trim video segment (FFmpeg)
   ├─▶ Optionally burn in captions (FFmpeg + ASS subtitles)
   ├─▶ Upload to object storage
   └─▶ Clip status: ready
```

---

## 6. Critical Risks & Gaps

### 6.1 Aspect Ratio / Reframing

**Problem:** Podcasts and long-form content are typically horizontal (16:9), but short-form platforms require vertical (9:16). Simply cropping the center cuts off important visual content.

**Options:**

| Option | Description | Complexity |
|--------|-------------|------------|
| Center crop | Simple center cut, loses sides | Low |
| Speaker detection + smart framing | Detect faces/speakers, auto-frame around them | High |
| Manual crop adjustment | Let user adjust crop area per clip | Medium |

**Recommendation:** Start with center crop for MVP, add manual adjustment as fast-follow. Speaker detection is a post-MVP enhancement.

### 6.2 Competition & Differentiation

**Existing competitors:**
- Opus Clip
- Vidyo.ai
- Munch
- Chopcast

**Our differentiation strategy:**

1. **Better clip selection** - Focus on superior AI-powered identification of viral moments. Invest heavily in prompt engineering and eventually fine-tuning to outperform competitors on clip quality.

2. **Competitive pricing** - Undercut established players on price while maintaining quality. Use aggressive free tier to acquire users, convert on value.

**Key insight:** Most competitors charge $20-50/month. There's room to compete on price while the market is still growing.

### 6.3 Legal / Copyright Considerations

**Risks:**
- Downloading YouTube videos via yt-dlp operates in a legal gray area
- Creating derivative content from others' videos has copyright implications
- YouTube ToS technically prohibits downloading

**Mitigations:**
- Terms of service requiring users to only process content they own or have rights to
- Consider YouTube API integration to verify channel ownership (future)
- Clear disclaimer shifting liability to users
- Consider limiting to videos where user can prove ownership

**Decision needed:** How strict to be on content ownership verification for MVP.

---

## 7. Pre-Build Validation

**Before building the full product, validate these critical assumptions:**

### 7.1 Clip Selection Quality (HIGHEST PRIORITY)

The entire value proposition depends on the AI identifying actually viral-worthy clips.

**Validation approach:**
1. Select 5-10 diverse podcasts (different topics, lengths, styles)
2. Manually extract transcripts
3. Test LLM prompts to identify clips
4. Manually review suggested clips - are they genuinely good?
5. Compare against what human editors would choose
6. Iterate on prompts until quality is consistently high

**Success criteria:** 70%+ of suggested clips are genuinely engaging moments a human editor would also select.

### 7.2 Processing Cost Model

Run the numbers before building to ensure unit economics work.

**Costs to estimate (per 1-hour video):**

| Component | Estimation Method |
|-----------|-------------------|
| Transcript extraction | YouTube API (free) vs Whisper API pricing |
| LLM analysis | Token count × API pricing |
| Video download/storage | Bandwidth + temporary storage |
| Video processing | Compute time for FFmpeg operations |
| Clip storage | Per-GB storage costs × retention period |

**Questions to answer:**
- What does it cost to process one video end-to-end?
- At what usage level does this become unsustainable on free tier?
- What price point makes this profitable?

### 7.3 Transcript Reliability

Test across diverse content to ensure transcript quality is sufficient.

**Test cases:**
- Videos with auto-captions available
- Videos without captions (Whisper fallback)
- Multiple speakers / crosstalk
- Technical jargon / niche vocabulary
- Non-native English speakers

---

## 8. MVP Scope

### 8.1 In Scope (MVP)

- [x] Google OAuth login
- [x] YouTube URL submission
- [x] Transcript extraction
- [x] LLM-based clip identification
- [x] Clip preview in browser
- [x] Raw clip download
- [x] Captioned clip download (3-4 presets)
- [x] Basic dashboard (job history)
- [x] 7-day clip retention
- [x] Basic aspect ratio handling (center crop to 9:16)

### 8.2 Out of Scope (Post-MVP)

- [ ] Additional input sources (file upload, Twitch, Spotify)
- [ ] Custom caption styling
- [ ] Team/organization accounts
- [ ] Public API access
- [ ] Direct publishing to social platforms
- [ ] Analytics on clip performance
- [ ] Fine-tuned prediction model
- [ ] Mobile app
- [ ] Smart speaker detection / auto-framing
- [ ] Manual crop adjustment per clip

---

## 9. Open Questions

| Question | Status | Notes |
|----------|--------|-------|
| Which LLM provider (OpenAI vs Anthropic)? | TBD | Needs cost/quality evaluation |
| Specific LLM prompting strategy? | TBD | Requires experimentation |
| Exact caption preset designs? | TBD | Design work needed |
| Whisper hosting (self-host vs API)? | TBD | Cost vs latency tradeoff |
| Target audience prioritization? | TBD | Learn from early users |
| Content ownership verification strictness? | TBD | Legal/ToS implications |
| Pricing strategy vs competitors? | TBD | Market research needed |

---

## 10. Success Metrics

### 10.1 Product Metrics

- **Activation:** % of signups who submit first video
- **Clip conversion:** % of suggested clips that get downloaded
- **Retention:** % of users returning within 7 days
- **Job completion rate:** % of jobs that complete successfully

### 10.2 Technical Metrics

- **Processing time:** Time from URL submit to clips ready
- **Transcript accuracy:** Quality of extracted transcripts
- **Prediction quality:** User feedback on clip suggestions (future)

---

## Appendix A: Caption Preset Examples

### Preset 1: Minimal
- Font: Inter
- Size: Medium
- Color: White with black outline
- Position: Bottom center
- Animation: None

### Preset 2: Bold
- Font: Montserrat Black
- Size: Large
- Color: White with shadow
- Position: Center
- Animation: Word-by-word highlight

### Preset 3: Colorful
- Font: Poppins Bold
- Size: Large
- Color: Yellow/accent colors
- Position: Center
- Animation: Word-by-word with color pop

### Preset 4: Subtle
- Font: Roboto
- Size: Small
- Color: White, semi-transparent background
- Position: Bottom
- Animation: Fade in/out

---

## Appendix B: Example LLM Prompt Structure

```
You are a viral content expert analyzing a podcast transcript to identify
clips that would perform well as short-form content on YouTube Shorts,
Instagram Reels, and TikTok.

## Current Trending Topics
{trending_topics}

## Transcript
{transcript}

## Instructions
Identify segments that would make engaging 15-90 second clips. Look for:
- Controversial or surprising statements
- Emotional moments (humor, inspiration, outrage)
- Actionable advice or insights
- Quotable one-liners
- Topics related to current trends
- Complete thoughts (don't cut mid-sentence)

For each clip, provide:
1. Start timestamp
2. End timestamp
3. Virality score (0-1)
4. Brief explanation of why this would perform well

Return only clips scoring above 0.6. Maximum 15 clips.

## Output Format
{output_schema}
```

---

*Document created: 2026-02-01*
*Last updated: 2026-02-01*
