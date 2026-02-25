# GitContext for VS Code

Visualize and manage AI context branches directly in VS Code.

## Features

- 🌿 **Branch visualization** - See all your context branches in a tree view
- 📝 **Commit browser** - Browse through commit history
- 🤖 **OTA log viewer** - View AI thought process logs
- 🔄 **Branch operations** - Create, switch, merge, delete branches
- ⚡ **Quick commands** - Keyboard shortcuts for common operations
- 🎨 **Rich webviews** - Detailed views for commits and OTA logs

## Installation

1. Install the GitContext Python package:
```bash
pip install gitcontext
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
