# arXiv Paper Reader

When asked to read, analyze, or summarize an arXiv paper, follow this systematic approach:

## 1. Paper Access
- Accept paper identifiers in formats:
  - Full URL: `https://arxiv.org/abs/2401.12345`
  - Short ID: `2401.12345`
  - Versioned: `2401.12345v2`
- Construct the abstract page URL: `https://arxiv.org/abs/{paper_id}`
- Access the PDF at: `https://arxiv.org/pdf/{paper_id}.pdf`
- Access the HTML5 version at: `https://arxiv.org/html/{paper_id}`

## 2. Search Capability
When searching for papers by keywords:
- Use the arXiv search API: `https://arxiv.org/search/?query={keywords}&searchtype=all`
- Perform web searches with site filter: `site:arxiv.org {keywords}`
- Extract paper IDs, titles, and authors from search results
- Present results in a structured format with links

## 3. Information Extraction
Gather the following from the abstract page:
- **Title**: Full paper title
- **Authors**: List of authors and their affiliations
- **Submitted Date**: Original submission date
- **Last Updated**: Most recent revision date
- **Abstract**: Full abstract text
- **Subjects**: arXiv categories (e.g., cs.AI, cs.LG)
- **Comments**: Conference info, page count, etc.

## 4. Paper Analysis
When analyzing the paper:

### Quick Summary
- What problem does this paper address?
- What is the proposed solution/approach?
- What are the key contributions?

### Technical Depth (if accessible)
- Methodology overview
- Key algorithms or architectures proposed
- Experimental setup and datasets used
- Main results and comparisons to prior work
- Limitations acknowledged by authors

### Critical Assessment
- Novelty: What's genuinely new?
- Rigor: How thorough is the evaluation?
- Reproducibility: Is code/data available?
- Impact: Potential influence on the field

## 5. Output Format

### For Single Paper Analysis
```
## 📄 [Paper Title]

**Authors:** [Author list]
**arXiv ID:** [ID]
**Submitted:** [Date]
**Subjects:** [Categories]

### Abstract
[Full abstract]

### 🎯 Key Contributions
[Bullet points of main contributions]

### 📊 Summary
- **Problem:** [What problem they're solving]
- **Approach:** [Their method]
- **Results:** [Key findings]

### 💡 Insights & Assessment
- **Novelty:** [Assessment]
- **Strengths:** [What's good]
- **Limitations:** [What's missing or weak]
- **Relevance:** [Who should care]

### 🔗 Links
- [Abstract Page](https://arxiv.org/abs/{paper_id})
- [PDF](https://arxiv.org/pdf/{paper_id}.pdf)
- [HTML5](https://arxiv.org/html/{paper_id})
```

### For Search Results
```
## 🔍 Search Results: "[Query]"

Found [N] relevant papers:

### 1. [Paper Title]
**Authors:** [Authors] | **ID:** [arXiv ID] | **Date:** [Date]
**Abstract:** [Brief excerpt...]
[Abstract] | [PDF] | [HTML5]

### 2. [Paper Title]
...
```

## 6. Use Cases
- "Read the arXiv paper 2401.12345"
- "Summarize this paper: https://arxiv.org/abs/2401.12345"
- "Search arXiv for papers on AI agents"
- "Find recent papers on transformer architectures and summarize the top results"
- "What's new in the latest paper by [author] on arXiv?"
- "Compare these two arXiv papers: [ID1] and [ID2]"

## Notes
- For PDF content, use HTTP requests to fetch and describe what's accessible
- The HTML5 version is often more readable for quick scanning
- If full PDF parsing isn't possible, work from the abstract and any available metadata
- Always provide direct links for the user to access the original paper
- When searching, prioritize recent and highly-cited papers