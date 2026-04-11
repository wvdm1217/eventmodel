---
description: "Use when writing or modifying Python code in the application. Covers modern Python standards, type safety, and developer experience."
name: "Modern Python & DX"
applyTo: "**/*.py"
---

# Modern Python & Developer Experience

## Type Safety & Data Modeling
- **Strict Typing**: Always use type hints for function arguments, return values, and variables.
- **Pydantic First**: Rely on `pydantic` (`>=2.12`) for data validation, parsing, and complex domain models. 

## Code Quality & Tooling
- **Ruff Compliance**: Write code that adheres to standard `ruff` formatting and linting rules without needing `# noqa` overrides unless strictly necessary.
- **Modern Syntax**: The project requires Python `>=3.14`. Use the latest standard library features, modern typing syntax (e.g., `|` for unions, `list[T]`), and new language constructs.

## Developer Experience (DX)
- **Readability**: Prioritize code readability. Use descriptive, unabbreviated variable and function names.
- **Contextual Documentation**: Write concise docstrings explaining the *why* (context, edge cases) rather than the *what* (which the code itself should make clear).
- **Zero Boilerplate**: Keep logic concise. Avoid unnecessary classes or abstractions when a simple function suffices.

## Testing
- **Pytest**: Write tests using `pytest`. Keep tests atomic, fast, and easy to run locally.
