# Community Pulse

When asked about opinions, recommendations, experiences, or "what do people think about X", gather community perspectives from Reddit and cross-reference with other sources.

## 1. Identify Target Communities
Based on the topic, determine relevant subreddits:
- **Programming**: python, javascript, rust, golang, programming, webdev, devops
- **Tech**: technology, sysadmin, homelab, selfhosted, linux
- **AI/ML**: MachineLearning, artificial, LocalLLaMA, ChatGPT
- **Products**: BuyItForLife, gadgets, or product-specific subreddits
- **Career**: cscareerquestions, ExperiencedDevs, ITCareerQuestions
- **General**: askreddit, NoStupidQuestions, explainlikeimfive

## 2. Gather Discussions
Use `reddit_search` with multiple approaches:
- **Broad search** (action: `search`): find relevant posts across all of Reddit
- **Targeted subreddit** (action: `subreddit`): browse specific communities
- **Deep dive** (action: `post`): read top posts with full comment threads

Search strategy:
- Try `sort=relevance` first for the query
- Also try `sort=top` with `time_filter=year` for the most upvoted takes
- Read 2–3 top posts fully (action: `post`) to get comment-level detail

## 3. Cross-Reference
- Use `web_search` to verify factual claims from Reddit comments
- Check if community opinions align with expert reviews or official docs
- Note where Reddit consensus differs from mainstream sources

## 4. Synthesis

```
## 🗣️ Community Pulse: "[Topic]"

### TL;DR
[One-paragraph summary of the community sentiment]

### Community Consensus
- ✅ [Point most people agree on]
- ✅ [Another widely shared view]

### Common Recommendations
- **Most recommended:** [Top pick with reasoning]
- **Runner-up:** [Second choice]
- **Budget option:** [If applicable]

### Dissenting Views
- ⚠️ [Notable minority opinion with reasoning]
- ⚠️ [Counter-argument to the consensus]

### Frequently Mentioned Concerns
- [Common complaint or caveat]
- [Another recurring issue]

### Notable Comments
> "[Insightful quote from a commenter]"
> — u/[username] in r/[subreddit] ([score] pts)

### Confidence Assessment
- **Sample size:** [How many posts/comments reviewed]
- **Recency:** [How recent the discussions are]
- **Agreement level:** [High/Medium/Low consensus]

### Sources
1. "[Post title]" — r/[subreddit] ([score] pts, [comments] comments) — [URL]
2. "[Post title]" — r/[subreddit] ([score] pts, [comments] comments) — [URL]
```

## Use Cases
- "What does Reddit think about [tool/product/framework]?"
- "What's the best [category] according to Reddit?"
- "Has anyone had experience with [service/product]?"
- "What are common complaints about [X]?"
- "What do developers recommend for [use case]?"

## Notes
- Reddit skews technical and opinionated — note this bias in your assessment
- High upvote counts indicate agreement but not necessarily correctness
- Look for comments from users who share actual experience, not just opinions
- Recency matters — a 3-year-old recommendation may be outdated
- When opinions are polarized, present both sides fairly
