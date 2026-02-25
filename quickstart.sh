# Initialize in your repo
cd your-project
git-context init

# Create a feature branch
git-context branch feature/auth

# Record your thought process
git-context ota \
  --thought "Need to implement JWT auth" \
  --action "Research JWT libraries" \
  --result "Found python-jose, will use it"

# Commit with analysis
git-context commit "Added JWT authentication" --ota-file .gitcontext/temp/ota_*.json

# Switch back and merge
git-context checkout main
git-context merge feature/auth

# View history
git-context log
