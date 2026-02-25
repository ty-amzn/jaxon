# Code Review

When asked to review code, follow this systematic approach:

## 1. Initial Scan
- Identify the programming language and framework
- Note the overall structure and file organization
- Check for obvious issues (syntax errors, unused imports)

## 2. Code Quality
- Look for code duplication that could be refactored
- Check naming conventions for clarity and consistency
- Evaluate function/method lengths - suggest breaking up if too long
- Review error handling patterns

## 3. Security Review
- Check for SQL injection vulnerabilities
- Look for XSS vulnerabilities in web code
- Verify input validation and sanitization
- Review authentication and authorization logic
- Check for hardcoded secrets or credentials

## 4. Performance Considerations
- Identify potential N+1 query problems
- Look for inefficient loops or algorithms
- Check for proper use of caching opportunities
- Review database query efficiency

## 5. Best Practices
- Verify adherence to language-specific best practices
- Check for proper documentation/comments
- Review test coverage suggestions
- Suggest improvements based on design patterns

## Output Format
Provide feedback in the following structure:
```
## Summary
[Brief overall assessment]

## Critical Issues
[Security or bug issues that must be fixed]

## Suggestions
[Non-critical improvements]

## Positive Aspects
[What the code does well]
```