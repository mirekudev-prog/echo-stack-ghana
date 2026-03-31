# EchoStack Deployment Guide

## Secure GitHub Push (Without Sharing Tokens)

Since you cannot share your token in the chat, follow these steps to deploy securely using your local terminal.

### Option 1: Using the Provided Script (Recommended)

1. **Edit the Script**:
   Open `deploy_to_github.sh` and update lines 12-14 with your details:
   ```bash
   REPO_OWNER="your-github-username"
   REPO_NAME="echostack"
   BRANCH="main"
   ```

2. **Make Script Executable**:
   ```bash
   chmod +x deploy_to_github.sh
   ```

3. **Set Environment Variable & Run**:
   *On Mac/Linux:*
   ```bash
   export GITHUB_TOKEN=github_pat_YOUR_TOKEN_HERE
   ./deploy_to_github.sh
   ```

   *On Windows (PowerShell):*
   ```powershell
   $env:GITHUB_TOKEN="github_pat_YOUR_TOKEN_HERE"
   bash deploy_to_github.sh
   ```

### Option 2: Manual Git Commands

If you prefer manual control:

1. **Set Token Temporarily**:
   ```bash
   export GITHUB_TOKEN=github_pat_YOUR_TOKEN_HERE
   ```

2. **Update Remote URL**:
   ```bash
   git remote set-url origin https://${GITHUB_TOKEN}@github.com/YOUR_USERNAME/echostack.git
   ```

3. **Push Changes**:
   ```bash
   git add .
   git commit -m "Update dashboard, admin panel, and backend endpoints"
   git push origin main
   ```

4. **Revert Remote URL (Clean Up)**:
   ```bash
   git remote set-url origin https://github.com/YOUR_USERNAME/echostack.git
   unset GITHUB_TOKEN
   ```

### Required Token Permissions
Ensure your Fine-grained Personal Access Token has:
- **Repository**: `Contents` (Read and write)
- **Repository**: `Pull requests` (Read and write) - Optional if only pushing directly

### Next Steps After Push
Once pushed to GitHub:
1. Go to your hosting provider (Render/Railway/Vercel).
2. Trigger a new deployment from the latest commit.
3. Verify environment variables (`SUPABASE_URL`, `SUPABASE_KEY`, etc.) are set in the hosting dashboard.
