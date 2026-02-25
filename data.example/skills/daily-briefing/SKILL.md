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

## 4. Output Format

```
## ☀️ Daily Briefing — [Date]

### 📅 Today's Schedule
- [Time] — [Event/Meeting]
- [Time] — [Event/Meeting]
- Free block: [Time range]

### 📰 News & Updates

#### [Topic 1]
- [Key development with source]
- [Related discussion or reaction]

#### [Topic 2]
- [Key development with source]

### 💬 Community Buzz
- [Interesting Reddit discussion relevant to user's interests]
- [Trending topic in their field]

### ✅ Reminders
- [Any scheduled reminders for today]
- [Upcoming deadlines this week]
```

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
- Keep it concise — this is a scan-and-go document, not deep research
- Prioritize actionable items (meetings, deadlines) over general news
- If the user hasn't specified interests, ask what topics they want tracked
- Store briefing preferences in memory for future personalization
