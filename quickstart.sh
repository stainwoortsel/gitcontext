# Initialize in your project
cd your-project
git-context init

# Create a feature branch
git-context branch feature/auth

# Record your thought process
git-context ota --interactive

# Commit with analysis
git-context commit "Added JWT authentication" --interactive

# View history
git-context log

# Switch back and merge
git-context checkout main
git-context merge feature/auth