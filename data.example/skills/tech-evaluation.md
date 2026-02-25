# Tech Evaluation

When asked to evaluate a library, framework, tool, service, or technology, conduct a multi-source investigation and produce a structured assessment.

## 1. Information Gathering

Collect data from multiple sources in parallel:

### Web Search (`web_search`)
- Official documentation and feature list
- Benchmark comparisons
- Known issues and limitations
- Licensing and pricing

### Reddit (`reddit_search`)
- Search for "[tech name] vs" to find comparison discussions
- Browse relevant subreddits for experience reports
- Look for "moved from X to Y" migration stories
- Check for common pain points in comments

### YouTube (`youtube_search`)
- Tutorial and walkthrough videos (gauge ecosystem health)
- Review/comparison videos from respected channels
- Conference talks by maintainers (for open-source projects)
- Extract transcripts from the most relevant 1–2 videos

### arXiv (`arxiv_search`)
- Only if the technology has an academic component (ML frameworks, algorithms, databases)
- Look for the original paper and benchmark studies

## 2. Evaluation Criteria

Assess across these dimensions:

| Dimension | What to Check |
|-----------|--------------|
| **Maturity** | Version number, release history, age, stability |
| **Community** | GitHub stars, contributors, Reddit activity, Stack Overflow questions |
| **Documentation** | Quality, completeness, examples, tutorials |
| **Performance** | Benchmarks, scalability, resource usage |
| **DX** | API design, error messages, debugging, learning curve |
| **Ecosystem** | Plugins, integrations, compatible tools |
| **Maintenance** | Commit frequency, issue response time, roadmap |
| **Alternatives** | Direct competitors, trade-offs of each |

## 3. Output Format

```
## 🔍 Tech Evaluation: [Technology Name]

### Overview
[What it is, what problem it solves, who makes it]

### Verdict: [👍 Recommended / 🤔 Conditional / 👎 Avoid]
[One-sentence summary of the recommendation]

### Strengths
- ✅ [Strength 1 with evidence]
- ✅ [Strength 2 with evidence]

### Weaknesses
- ❌ [Weakness 1 with evidence]
- ❌ [Weakness 2 with evidence]

### Community Sentiment
[Summary of what practitioners say — from Reddit, YouTube, forums]

### Comparison with Alternatives

| Feature | [This Tech] | [Alternative A] | [Alternative B] |
|---------|-------------|-----------------|-----------------|
| [Criterion 1] | ... | ... | ... |
| [Criterion 2] | ... | ... | ... |

### Best For
- [Use case where this is the right choice]
- [Another good fit]

### Avoid If
- [Scenario where this is a poor choice]
- [Another mismatch]

### Sources
1. [Source with URL]
2. [Source with URL]
```

## Use Cases
- "Should I use [framework] for my project?"
- "Compare [X] vs [Y] vs [Z]"
- "Is [technology] production-ready?"
- "What's the best [category] for [use case]?"
- "Evaluate [tool] for [specific requirement]"

## Notes
- Always check the date of sources — tech ecosystems change fast
- Distinguish between "popular" and "good" — hype doesn't equal quality
- Consider the user's specific context (team size, existing stack, scale) if known
- For fast-moving fields (AI/ML), weight recent sources much more heavily
- If comparing, ensure fair comparison (same version era, similar use cases)
