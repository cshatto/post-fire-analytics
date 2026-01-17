# Post-Fire Analytics

## Development Setup

This project uses:
- **uv** - Fast Python package installer and resolver
- **ruff** - Fast Python linter and formatter
- **mypy** - Static type checker

### Prerequisites

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

1. Create a virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On macOS/Linux
uv pip install -e ".[dev]"
```

### Code Quality Tools

#### Ruff (Linting and Formatting)

Check for linting issues:
```bash
ruff check .
```

Auto-fix linting issues:
```bash
ruff check --fix .
```

Format code:
```bash
ruff format .
```

#### Mypy (Type Checking)

Run type checking:
```bash
mypy post-fire-analytics
```

#### Running All Checks

```bash
ruff check . && ruff format --check . && mypy post-fire-analytics
```

### Testing

Run tests with pytest:
```bash
pytest
```
