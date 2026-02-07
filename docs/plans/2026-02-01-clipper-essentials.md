# Clipper - Essentials

**Date:** 2026-02-01

---

## What We're Building

A web app that takes YouTube video URLs and automatically identifies + extracts viral-worthy short-form clips with optional captions.

**Input:** YouTube URL
**Output:** 10-15 clips (15-90 sec each), downloadable as raw or captioned video

---

## Core Requirements

| Requirement | Decision |
|-------------|----------|
| Input source | YouTube only (MVP) |
| Auth | Google OAuth, required |
| Clip duration | 15-90 seconds, natural content boundaries |
| Clip selection | Threshold-based, max 10-15 per video |
| Output formats | Raw + captioned (user choice) |
| Caption styles | 3-4 presets |
| Aspect ratio | Center crop to 9:16 (MVP) |
| Storage | 7 days default |

---

## AI Approach

**Decision needed:** How to identify viral clips from transcript.

| Option | Description |
|--------|-------------|
| LLM with prompting | GPT-4/Claude with crafted prompts + trending context |
| Fine-tuned LLM | Train on viral vs non-viral examples |
| Custom classifier | Build from scratch on engagement features |

**Recommendation:** Start with LLM prompting, validate, then consider fine-tuning.

### Trending Data Sources (MVP)

- Google Trends via pytrends (free, rate-limited)
- YouTube Trending via Data API

---

## Critical Risks

### 1. Aspect Ratio
Podcasts are 16:9, shorts need 9:16. MVP uses center crop. Smart speaker framing is post-MVP.

### 2. Competition
Opus Clip, Vidyo.ai, Munch exist. Our angle:
- **Better clip selection** - superior AI identification
- **Competitive pricing** - undercut on price

### 3. Legal Gray Area
Downloading YouTube videos via yt-dlp has ToS implications. Mitigation: require users to confirm content ownership.

---

## Pre-Build Validation

**Do these BEFORE building the full product:**

### 1. Clip Selection Quality (CRITICAL)

Test if the AI can actually pick good clips:
1. Get 5-10 podcast transcripts
2. Run through LLM prompts
3. Review suggested clips manually
4. Iterate until 70%+ are genuinely good picks

### 2. Cost Model

Estimate per-video costs:
- Transcript: YouTube API (free) vs Whisper
- LLM: Token count × pricing
- Video processing: FFmpeg compute
- Storage: Per-GB × retention

### 3. Transcript Reliability

Test across:
- Videos with/without auto-captions
- Multiple speakers
- Technical jargon
- Non-native speakers

---

## Open Questions

| Question | Notes |
|----------|-------|
| LLM provider (OpenAI vs Anthropic)? | Cost/quality evaluation needed |
| Prompting strategy? | Requires experimentation |
| Caption preset designs? | Design work needed |
| Whisper: self-host vs API? | Cost vs latency |
| Content ownership verification? | How strict for MVP? |
| Pricing vs competitors? | Market research needed |

---

## MVP Scope

**In:**
- Google OAuth
- YouTube URL input
- Transcript extraction
- LLM clip identification
- Clip preview
- Raw + captioned download
- 3-4 caption presets
- Center crop (9:16)
- 7-day retention

**Out:**
- Other input sources
- Custom captions
- Teams/orgs
- Public API
- Direct social publishing
- Smart speaker framing
- Manual crop adjustment
