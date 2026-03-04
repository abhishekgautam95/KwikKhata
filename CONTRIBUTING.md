# Contributing to KwikKhata

Thank you for your interest in contributing! This guide will help you get started.

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/KwikKhata.git
   cd KwikKhata
   ```
3. **Create a branch** for your change:
   ```bash
   git checkout -b feat/my-feature
   ```

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env               # fill in required values
```

Or simply use the Makefile:
```bash
make install
```

## Running Tests

```bash
make test
# or directly:
pytest
```

All tests live under `tests/` and follow the `test_*.py` naming convention.

## Code Style

KwikKhata uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
make lint      # check for lint issues
make format    # auto-format code
```

Please make sure both commands pass before opening a pull request.

## Type Checking

```bash
make typecheck
```

## Pull Request Process

1. Ensure all tests pass and the linter reports no errors.
2. Update `README.md` and docstrings if your change affects public behaviour.
3. Open a pull request against the `main` branch with a clear description of the problem and solution.
4. A maintainer will review your PR within a few days.

## Reporting Bugs

Please [open an issue](https://github.com/abhishekgautam95/KwikKhata/issues/new) with:
- A clear title and description.
- Steps to reproduce the problem.
- Expected vs. actual behaviour.
- Your Python version and OS.
