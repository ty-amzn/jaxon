# Fact Check

When asked to verify, fact-check, or confirm a claim, statement, or piece of information, follow this systematic approach:

## 1. Claim Identification
- Clearly state the claim or statement being verified
- Identify the key components/facts within the claim
- Note any ambiguous terms that need clarification

## 2. Search Strategy
Perform multiple targeted searches:
- **Primary search**: Direct query about the claim
- **Source search**: Look for original sources, studies, or official statements
- **Counter-evidence search**: Actively look for opposing viewpoints or debunking
- **Context search**: Gather background information

## 3. Source Evaluation
Assess source credibility using:
- **Authority**: Is the source an expert or official organization?
- **Reputation**: Is it a trusted publication or platform?
- **Recency**: How current is the information?
- **Corroboration**: Do multiple independent sources agree?
- **Bias**: Is there obvious bias or agenda?

### Source Credibility Tiers
| Tier | Examples | Weight |
|------|----------|--------|
| 🔵 **Tier 1** | Academic papers, official government/organization reports, court documents, primary sources | Highest |
| 🟢 **Tier 2** | Reputable news outlets (Reuters, AP, BBC, NYT, etc.), established industry publications | High |
| 🟡 **Tier 3** | Opinion pieces, blogs, social media posts, secondary reporting | Moderate |
| 🔴 **Tier 4** | Anonymous sources, unverified claims, known unreliable sites | Low/None |

## 4. Verification Process

### For Statistical Claims
- Find the original data source
- Check methodology and sample size
- Verify the numbers are used in proper context
- Note any conflicting data

### For Scientific Claims
- Locate the peer-reviewed paper (check arXiv, PubMed, etc.)
- Verify journal reputation and impact
- Check for replications or rebuttals
- Note if findings are consensus or controversial

### For News/Current Events
- Check multiple independent news sources
- Look for official statements or press releases
- Verify images/videos (check for manipulation)
- Note corrections or updates to original reporting

### For Historical Claims
- Consult multiple historical sources
- Check primary documents when possible
- Note historian consensus
- Identify any historical debate

### For Quotes
- Find original source/speech
- Verify context (was it paraphrased or selective?)
- Check if quote is accurate or misattributed
- Look for full context

## 5. Output Format

```
## 🔍 Fact Check: "[Original Claim]"

### 📋 Claim Summary
[Brief restatement of what's being checked]

### ✅ Verdict
[TRUE / MOSTLY TRUE / PARTLY TRUE / MISLEADING / FALSE / UNVERIFIABLE]

### 🔎 Evidence

**Supporting Evidence:**
- [Finding 1 with source citation]
- [Finding 2 with source citation]

**Contradicting/Contextual Evidence:**
- [Finding 1 with source citation]
- [Finding 2 with source citation]

### 📊 Analysis
- **What's accurate:** [Components that check out]
- **What's inaccurate:** [Components that don't]
- **Missing context:** [Important context not in original claim]

### 📚 Sources
1. [Source title](URL) - [Tier rating] - [Date]
2. [Source title](URL) - [Tier rating] - [Date]

### 💡 Bottom Line
[Clear, concise summary of findings]
```

## 6. Special Cases

### Claim is Unverifiable
If insufficient evidence exists:
- Clearly state "UNVERIFIABLE"
- Explain why (limited sources, classified info, lack of data, etc.)
- Provide what partial information is available

### Claim Has Nuance
For complex topics:
- Break down into component claims
- Rate each component separately
- Provide nuanced overall assessment

### Claim is Rapidly Evolving
For breaking news or developing stories:
- Note timestamp of verification
- Highlight that situation is developing
- Recommend checking for updates

## 7. Use Cases

| Command | Action |
|---------|--------|
| "Fact check: [statement]" | Full verification of a claim |
| "Is it true that [claim]?" | Verify a specific assertion |
| "Verify this claim: [quote/statistic]" | Check a quote or number |
| "What's the real story behind [headline]?" | Deep dive into a news item |
| "Check if [company/person] actually said [quote]" | Quote verification |

## 8. Best Practices

- **Be thorough**: Don't stop at one source
- **Consider bias**: Check both sides of controversial topics
- **Show your work**: Link all sources used
- **Acknowledge limits**: Be transparent about uncertainty
- **Stay neutral**: Present findings objectively without editorializing
- **Prioritize recent info**: For evolving situations, prioritize the latest
- **Don't cherry-pick**: Present all relevant evidence, not just what confirms

## Notes

- When checking scientific claims, apply the arxiv-reader skill if relevant
- For complex claims, break them into smaller verifiable components
- Always provide direct links so the user can review sources themselves
- If a claim is worded ambiguously, check multiple interpretations