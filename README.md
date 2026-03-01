# Wikify

A tool for extracting structured knowledge from notes and generating
Wikipedia-style articles. The pipeline is intentionally light-weight: input is
plain-text files, the database is a set of JSON files, and output is in
Markdown. Human control is accomplished through version control of the knowledge
repo.

The original knowledge domain for this project is a long-running D&D game I’m
playing with by brother Rogers and friend Thain. It’s Thain’s game, set in an
original world he created called Aral. Rogers takes moment-by-moment notes of
our adventures in Discord. Those session notes are then grist to the wiki mill.

Currently, this is a toy application to scratch a personal itch. Once I get it
working, I’m also interested in using it as a testbed for practical discovery of
what models are sufficient to this use case.

## Setup

```bash
git clone --recursive git@github.com:whittle/wikify.git
cd wikify
uv sync
```

If you already cloned without `--recursive`:

```bash
git submodule update --init
```

## Configuration

### Anthropic API Key

The extraction and rendering stages use Claude via the Anthropic API. Set your API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="sk-ant-xxxxx"
```

You can add this to your shell profile (`~/.zshrc`), a `.env` file, or use [direnv](https://direnv.net/) with a `.envrc` file. Never commit API keys to version control.

## Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. The hooks run automatically on `git commit`, but you can also run them manually:

```bash
pre-commit run          # Run on staged files
pre-commit run --all    # Run on all files (use when updating hooks)
```

The following checks must pass before committing:

- **trailing-whitespace**: Remove trailing whitespace
- **end-of-file-fixer**: Ensure files end with a newline
- **check-yaml**: Validate YAML syntax
- **check-added-large-files**: Prevent large files from being committed
- **uv-lock**: Keep uv.lock in sync
- **uv-export**: Keep requirements exports in sync
- **ruff-check**: Lint Python code (with auto-fix)
- **ruff-format**: Format Python code
- **ty-check**: Type check with ty
- **pytest**: Run the test suite
