#!/bin/bash

# Secure Deployment Script for EchoStack
# Uses GITHUB_TOKEN from environment variables

# 1. Check if Token is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ Error: GITHUB_TOKEN environment variable is not set."
    echo "   Please run: export GITHUB_TOKEN=github_pat_..."
    exit 1
fi

# 2. Configuration (Update these if your repo details differ)
REPO_OWNER="YOUR_GITHUB_USERNAME"
REPO_NAME="echostack"
BRANCH="main"

echo "🚀 Starting secure deployment for $REPO_OWNER/$REPO_NAME..."

# 3. Configure Git Remote with Token (Temporary)
# This avoids saving the token in .git/config permanently
REMOTE_URL="https://${GITHUB_TOKEN}@github.com/${REPO_OWNER}/${REPO_NAME}.git"

# Check if remote exists, if not add it, otherwise update it
if git remote get-url origin > /dev/null 2>&1; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi

# 4. Stage, Commit, and Push
git add .
git commit -m "chore: Update dashboard, admin panel, and backend endpoints"

if [ $? -eq 0 ]; then
    echo "✅ Changes committed successfully."
    
    # Ensure we are on the correct branch
    git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"
    
    echo "⬆️ Pushing to GitHub..."
    git push origin "$BRANCH"
    
    if [ $? -eq 0 ]; then
        echo "🎉 Deployment successful! Check your repo at:"
        echo "   https://github.com/${REPO_OWNER}/${REPO_NAME}"
    else
        echo "❌ Push failed. Check your token permissions (needs 'Contents: Read/Write')."
        exit 1
    fi
else
    echo "⚠️ No changes to commit or commit failed."
fi

# 5. Cleanup: Revert remote URL to standard HTTPS (optional but cleaner)
STANDARD_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}.git"
git remote set-url origin "$STANDARD_URL"
echo "🔒 Token cleared from git config."
