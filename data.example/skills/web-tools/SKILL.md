---
name: web-tools
description: Guide for selecting the right web tool (web_search, web_fetch, browse_web, youtube, reddit, arxiv). Use when gathering information from the internet.
---
# Web Tools Guide

When gathering information from the internet, choose the right tool for the job. Using the wrong tool wastes time and produces worse results.

## Tool Selection

| Need | Tool | Why |
|------|------|-----|
| Find pages/articles about a topic | `web_search` | Broad discovery across the web |
| Read a specific webpage | `web_fetch` | Fast, extracts text from static pages |
| Read a JS-heavy page (SPA, dashboard) | `browse_web` (extract) | Renders JavaScript before extracting |
| Screenshot a page | `browse_web` (screenshot) | Visual capture of rendered page |
| Fill forms, click buttons | `browse_web` (click/fill) | Interactive browser automation |
| Find videos or video content | `youtube_search` (search) | YouTube-specific results with metadata |
| Read what a video says | `youtube_search` (transcript) | Extracts spoken content as text |
| Find community opinions/experiences | `reddit_search` (search) | Real user discussions and recommendations |
| Read a Reddit thread in depth | `reddit_search` (post) | Full post with top comments |
| Browse a specific community | `reddit_search` (subreddit) | See what a community is discussing |
| Find academic papers | `arxiv_search` | Searches arXiv with structured results |
| Read a PDF document | `pdf_read` | Extracts text from PDF files/URLs |

## Decision Flow

1. **Do I need a specific page?** → `web_fetch` (or `browse_web` if JS-heavy)
2. **Do I need to find pages?** → `web_search`
3. **Is the answer likely in a video?** → `youtube_search`
4. **Do I want real user experiences?** → `reddit_search`
5. **Is this academic/research?** → `arxiv_search` (then `pdf_read` for full papers)
6. **Do I need to interact with a site?** → `browse_web`

## Common Mistakes to Avoid

- **Don't use `browse_web` when `web_fetch` works.** `web_fetch` is faster and cheaper. Only use `browse_web` for pages that require JavaScript rendering.
- **Don't use `web_search` to read a page.** Search finds URLs; use `web_fetch` to read them.
- **Don't use `web_fetch` for YouTube videos.** Use `youtube_search` with `video_info` or `transcript` — you'll get structured data instead of a mess of HTML.
- **Don't use `web_search` for Reddit.** `reddit_search` returns structured posts and comments with scores. Web search just gives you links you'd then need to fetch.
- **Don't fetch an arXiv abstract page.** Use `arxiv_search` for discovery, then `pdf_read` for the full paper.

## Multi-Source Research Pattern

For thorough research on a topic, combine tools:

1. `web_search` — get the lay of the land, find authoritative sources
2. `web_fetch` — read the most relevant pages in detail
3. `reddit_search` — get practitioner perspectives and real-world experience
4. `youtube_search` — find explanations and tutorials (use transcript to read them)
5. `arxiv_search` — check for academic backing if relevant

Don't use all five for every question. Match the sources to what the user needs.
