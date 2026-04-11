---
name: review
description: 'Perform comprehensive code reviews on proposed changes, pull requests, or specified files. Focuses on security, performance, code quality, and idiomatic practices, providing structured, actionable feedback.'
argument-hint: 'Provide the branch, files, or PR to review'
---

# Code Review Process

## When to Use
- When the user asks to "review my code", "review this file", or "do a code review".
- Before committing or pushing significant code changes.
- To evaluate code quality, security, and performance.

## Review Principles
1. **Be Constructive & Actionable**: Provide specific suggestions and code examples rather than vague critiques.
2. **Prioritize**: Highlight critical issues (security, severe bugs) before stylistic nits.
3. **Idiomatic**: Suggest patterns and standard library usage appropriate for the specific language/framework.
4. **Thorough**: Check for edge cases, error handling, type safety, and performance bottlenecks.

## Code Review Workflow
When initiating a code review, follow this exact workflow:

### Step 1: Gather Context
- Identify the target files. If not provided, ask the user or check the active git changes using `git diff HEAD`.
- Understand the intent of the code (e.g., bug fix, new feature, refactoring).

### Step 2: Analyze the Code
Evaluate the target code across these five dimensions:
- **Security**: Vulnerabilities, injection risks, hardcoded secrets, improper authorization checks.
- **Performance**: Algorithmic complexity, memory leaks, unnecessary allocations, N+1 queries.
- **Correctness & Edge Cases**: Off-by-one errors, null/None pointer exceptions, unhandled exceptions, race conditions.
- **Maintainability**: DRY principles, naming conventions, cyclomatic complexity, modularity, testability.
- **Typing & Documentation**: Missing type hints, unclear docstrings, misleading comments.

### Step 3: Present the Review
Output the review in a clear, structured Markdown format. Use the following template:

#### Code Review Summary
*A brief summary of what the code does and overall impressions.*

#### 🚨 Critical Issues (Security, Bugs, Performance)
*(Exclude section if none. Highlight major problems that must be fixed).*
- **[File/Line]**: Issue description. Provide a code block showing the fix.

#### 💡 Suggestions & Improvements
*Go through the issues file-by-file or logically.*
*For each issue:*
- **[Category]**: Brief description.
- **Why**: Explain why it's an issue.
- **Suggestion**: Provide the actionable fix with a before/after code example.

#### 📚 Nitpicks & Style (Optional)
*Minor stylistic suggestions, naming conventions, etc.*

### Step 4: Next Steps
- Ask the user if they would like you to automatically apply any of the suggested changes to the files.