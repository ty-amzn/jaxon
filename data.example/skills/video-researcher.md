# Video Researcher

When asked to learn about a topic from video content, or when video explanations would be valuable, follow this approach:

## 1. Discovery
- Search YouTube for the topic with `youtube_search` (action: `search`)
- Target 5–8 results to get a good spread of perspectives
- Prioritize videos with high view counts and from reputable channels

## 2. Screening
Review the search results and select the 2–4 most relevant videos based on:
- **Relevance**: Title and channel match the topic
- **Authority**: Established channels, known experts, conference talks
- **Recency**: Prefer recent content unless the topic is timeless
- **Length**: Longer videos (10min+) tend to have more depth

## 3. Transcript Extraction
For each selected video:
- Use `youtube_search` (action: `transcript`) to pull the transcript
- If no English transcript is available, fall back to `youtube_search` (action: `video_info`) for description and chapters

## 4. Synthesis
Analyze transcripts and produce a structured summary:

```
## 🎬 Video Research: "[Topic]"

### Key Takeaways
- [Main insight 1]
- [Main insight 2]
- [Main insight 3]

### Detailed Findings

#### [Subtopic A]
[Synthesized information from multiple videos]
- Source: "[Video Title]" by [Channel] — [URL]

#### [Subtopic B]
[Synthesized information from multiple videos]
- Source: "[Video Title]" by [Channel] — [URL]

### Points of Agreement
- [What multiple creators agree on]

### Points of Disagreement
- [Where creators differ, with both perspectives]

### Recommendations from Creators
- [Actionable advice extracted from videos]

### Sources
1. "[Video Title]" by [Channel] ([Duration]) — [URL]
2. "[Video Title]" by [Channel] ([Duration]) — [URL]
```

## 5. Memory
- Store key findings with `memory_store` if the user is likely to reference this topic again
- Note which videos were most useful for potential follow-up

## Use Cases
- "What are the best practices for X? Check YouTube"
- "Find me video explanations of [concept]"
- "What are YouTubers saying about [product/technology]?"
- "Summarize this YouTube video: [URL]"
- "Learn about [topic] from conference talks"

## Notes
- Always provide video URLs so the user can watch the originals
- When a transcript is too long, focus on the introduction, key sections, and conclusion
- If the user provides a specific URL, go straight to transcript extraction
- Cross-reference video claims with web search when accuracy matters
