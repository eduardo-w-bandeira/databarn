# Contributing

Thanks for your interest in DataBarn.

## Setup

- Python **3.12+** is required.
- Create a virtual environment, then install the package in editable mode with dev dependencies:

```bash
pip install -e ".[dev]"
```

## Tests

```bash
pytest tests
```

Pull requests that change behavior should include or update tests for the affected code paths.

## Style

Match the existing code style and naming in the files you touch. Prefer focused changes over large refactors unless discussed first.
