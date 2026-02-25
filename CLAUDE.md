# 🤖 Project Guidelines & Context for Claude Code

## 🛠️ Tech Stack & Toolchain
- **Package Manager**: `uv` (Fast Python package installer and resolver)
- **Language**: Python 3.12+ (Strict Type Hints Required)
- **Testing**: `pytest` + `pytest-cov`
- **Linting/Formatting**: `ruff`
- **Version Control**: Git

## ⚡ Operational Commands
All commands must be executed via `uv`.
- **Run Tests**: `uv run pytest` (or `uv run pytest tests/test_specific.py`)
- **Lint Code**: `uv run ruff check .`
- **Format Code**: `uv run ruff format .`
- **Run App**: `uv run python src/main.py`
- **Add Dependency**: `uv add <package>` (Ask before adding!)

## 🧬 Development Workflow (Strict TDD)
You must follow the **Red-Green-Refactor** cycle for every task:

1.  **PLAN**: briefly explain your implementation plan and file structure changes.
2.  **RED**: Write a failing test case in `tests/`. Run it to confirm failure.
3.  **GREEN**: Write the *minimal* code in `src/` to pass the test.
4.  **REFACTOR**: Optimize code, add type hints, docstrings. Run `uv run ruff check .`.
5.  **COMMIT**: Create a git commit using Conventional Commits.

## 📝 Coding Standards (Non-negotiable)

### 1. Type Hints & Docstrings
- **Strict Typing**: All function arguments and return values MUST have type hints.
  - *Bad*: `def process(data):`
  - *Good*: `def process(data: dict[str, Any]) -> list[int]:`
- **Docstrings**: Use Google Style docstrings for all public modules, classes, and functions.

### 2. Architecture & Design
- **Modularity**: Keep functions small (Single Responsibility Principle).
- **No Global State**: Avoid global variables; use dependency injection if needed.
- **Path Handling**: Always use `pathlib.Path`, never string concatenation for paths.
- **Error Handling**: Use custom exceptions in `src/exceptions.py` rather than generic `Exception`.

### 3. Testing Rules
- **Structure**: Use `Arrange-Act-Assert` pattern in tests.
- **Independence**: Tests must not depend on each other or external execution order.
- **Mocking**: External APIs/DBs must be mocked. Do not make real network calls during tests.

## 📦 Git Commit Convention
Follow **Conventional Commits** format:
- `feat: description` (New feature)
- `fix: description` (Bug fix)
- `docs: description` (Documentation only)
- `refactor: description` (Code change that neither fixes a bug nor adds a feature)
- `test: description` (Adding missing tests or correcting existing tests)

## 🚫 Constraints (Don'ts)
- **DO NOT** remove existing comments unless they are obsolete.
- **DO NOT** leave `print()` statements for debugging; use `logging`.
- **DO NOT** hallucinate dependencies. If you need a library, ask permission to `uv add` it.
