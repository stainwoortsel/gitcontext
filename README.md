# GitContext 🧠📦

[![Tests](https://github.com/yourname/gitcontext/actions/workflows/tests.yml/badge.svg)](https://github.com/yourname/gitcontext/actions/workflows/tests.yml)
[![PyPI version](https://badge.fury.io/py/gitcontext.svg)](https://badge.fury.io/py/gitcontext)
[![Python versions](https://img.shields.io/pypi/pyversions/gitcontext.svg)](https://pypi.org/project/gitcontext/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Git for AI context management** - Track, version, and manage AI thoughts, decisions, and context alongside your code.

## Features

- 🌿 **Branch contexts** - Different AI contexts for different features
- 📝 **Commit thoughts** - Save OTA (Overthinking Analysis) logs
- 🔀 **Smart merging** - Squash detailed logs into summaries
- 🤖 **Multiple LLM providers** - OpenAI, Anthropic, Ollama, DeepSeek
- 🎯 **Decision tracking** - Record key decisions and rejected alternatives
- 🔗 **Git integration** - Works alongside your existing Git workflow
- 🖥️ **Beautiful CLI** - Rich terminal output with colors and tables
- 🐍 **Python API** - Use programmatically in your scripts

## Installation

```bash
# From PyPI
pip install gitcontext

# With specific LLM support
pip install "gitcontext[openai]"      # OpenAI support
pip install "gitcontext[anthropic]"   # Anthropic support
pip install "gitcontext[ollama]"      # Ollama support
pip install "gitcontext[all]"         # All providers

# From source
git clone https://github.com/yourname/gitcontext
cd gitcontext
pip install -e ".[dev]"
```

## Basic usage

Setup gitcontext
```bash
cd gitcontext
pip install -e .
```

Check this up
```bash
git-context --help
```

Let's start any project
```bash
cd ~/my-project
git-context init
```

Feature branch creation
```bash
git-context branch feature/new-api
```

Writing OTA log
```bash
git-context ota
```

Doing commit
```bash
git-context commit "Added new API endpoint"
```

Getting status
```bash
git-context status
```

Get log
```bash
git-context log
```

Merging
```bash
git-context merge feature/new-api
```
