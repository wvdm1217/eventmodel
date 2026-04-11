# Eventmodel Workspace Instructions

## Architecture & Project Structure
- **Core Library**: `src/eventmodel/` contains the framework for building type-safe, event-driven Python apps.
- **Examples**: `examples/` contains usage demonstrations. 
- **Design Philosophy**: Zero boilerplate. Prefer simple functions over complex abstractions unless absolutely necessary.

## Build and Test Commands
We use `uv` as our primary package and project manager. Agents should use these commands for tasks:
- **Run Examples**: `uv run examples/<filename>.py`
- **Linting & Formatting**: `uv run ruff check` and `uv run ruff format`
- **Type Checking**: `uv run ty check`
- **Testing**: `uv run pytest`

## Code Style & Conventions
- **Python Specifics**: See `.agents/instructions/python.instructions.md` for our modern Python 3.14+, strict typing, and Pydantic rules.
- **Developer Experience (DX)**: Maintain high readability. Code must act as its own documentation where possible. Use concise docstrings focusing on the *why*.
