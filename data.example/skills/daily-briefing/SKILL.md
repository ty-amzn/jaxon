---
name: daily-briefing
description: Compile a personalized daily digest from calendar, news, and community sources. Use for morning briefings.
---
# Daily Briefing

When asked for a morning briefing, daily summary, or "what's going on today", compile a personalized digest from multiple sources.

## 1. Calendar Check
- Use `calendar` (action: `today`) to get today's events
- Highlight upcoming meetings, deadlines, and time-sensitive items
- Note any gaps or free blocks in the schedule

## 2. Topics of Interest
- Use `memory_search` to recall the user's interests, ongoing projects, and topics they've asked about recently
- Build a list of 3–5 search topics based on what's relevant to them

## 3. News & Updates
For each topic of interest:
- Use `web_search` to find recent news and developments
- Use `reddit_search` (action: `search`, sort: `hot`, time_filter: `day`) for community discussions
- Focus on developments from the last 24 hours

## 4. Fact-Checking
Before including any news item, apply the `fact-check` skill to verify it. Drop items that turn out false, and flag anything unverifiable.

## 5. Tone & Format
Write the briefing in a **conversational, natural tone** — like a knowledgeable friend catching you up over coffee, not a formal report. Use the following structure loosely, but don't be rigid about it:

- **Schedule** — lead with what's on the calendar. Be brief, just the highlights and any heads-up ("Looks like you have back-to-back meetings this afternoon, so maybe grab lunch early.")
- **What's happening** — cover news and updates topic by topic. Explain *why* something matters, not just *what* happened. One or two sentences per item is fine. Include source links inline.
- **Community chatter** — anything interesting from Reddit or forums. Keep it light.
- **Heads up** — reminders, upcoming deadlines, anything to keep on the radar this week.

Avoid:
- Bullet-point walls — use them sparingly, prefer short paragraphs
- Emoji headers (like 📅 📰) — they make it feel like a template. A simple **bold heading** is fine.
- Repeating "Here's your briefing" or other filler — just start talking.

## Customization
The briefing adapts based on what's available:
- No calendar configured → skip the schedule section
- No specific interests in memory → use general tech/news topics
- Weekend → lighter briefing, skip work-related items

## Use Cases
- "Good morning" / "Morning briefing"
- "What's on my schedule today?"
- "Catch me up on what's happening"
- "Daily digest"

## Notes
- Keep it concise — this is a scan-and-go read, not deep research
- Prioritize actionable items (meetings, deadlines) over general news
- If the user hasn't specified interests, ask what topics they want tracked
- Store briefing preferences in memory for future personalization
