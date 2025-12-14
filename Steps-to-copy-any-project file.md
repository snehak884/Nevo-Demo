Here are ways to copy folders while excluding `.git` and `.terraform` directories.

## Solution: Copy folders excluding `.git` and `.terraform`

### Method 1: Using `rsync` (recommended)

```bash
# Copy folder excluding .git and .terraform
rsync -av --exclude='.git' --exclude='.terraform' \
  --exclude='*.tfstate' --exclude='*.tfstate.*' \
  --exclude='.terraform.lock.hcl' \
  /path/to/source/Nevo-Framwork-chat-bot/ \
  /path/to/destination/Nevo-Framwork-chat-bot/
```

For your case:
```bash
# From your current location
rsync -av --exclude='.git' --exclude='.terraform' \
  --exclude='*.tfstate' --exclude='*.tfstate.*' \
  --exclude='.terraform.lock.hcl' \
  /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/Nevo-Framwork-chat-bot/ \
  /path/to/new/location/Nevo-Framwork-chat-bot/
```

What this does:
- `-a`: Archive mode (preserves permissions, timestamps)
- `-v`: Verbose (shows what's being copied)
- `--exclude='.git'`: Skips `.git` directories
- `--exclude='.terraform'`: Skips `.terraform` directories
- `--exclude='*.tfstate'`: Skips Terraform state files

---

### Method 2: Using `find` and `cp` (alternative)

```bash
# Create destination directory
mkdir -p /path/to/destination/Nevo-Framwork-chat-bot

# Copy files excluding .git and .terraform
cd /path/to/source/Nevo-Framwork-chat-bot
find . -type f \
  ! -path '*/.git/*' \
  ! -path '*/.terraform/*' \
  ! -name '*.tfstate' \
  ! -name '*.tfstate.*' \
  ! -name '.terraform.lock.hcl' \
  -exec cp --parents {} /path/to/destination/Nevo-Framwork-chat-bot/ \;
```

---

### Method 3: Using `tar` with exclusions (good for one command)

```bash
# Create a tarball excluding .git and .terraform, then extract
cd /path/to/source
tar --exclude='.git' \
    --exclude='.terraform' \
    --exclude='*.tfstate' \
    --exclude='*.tfstate.*' \
    --exclude='.terraform.lock.hcl' \
    -czf nevo-chatbot-code-only.tar.gz Nevo-Framwork-chat-bot/

# Extract to destination
cd /path/to/destination
tar -xzf /path/to/source/nevo-chatbot-code-only.tar.gz
```

---

## Quick script for future use

Create a reusable script:

```bash
# Create a script file
cat > ~/copy-code-only.sh << 'EOF'
#!/bin/bash

# Usage: ./copy-code-only.sh <source> <destination>

SOURCE="$1"
DEST="$2"

if [ -z "$SOURCE" ] || [ -z "$DEST" ]; then
    echo "Usage: $0 <source_folder> <destination_folder>"
    exit 1
fi

# Create destination directory
mkdir -p "$DEST"

# Copy excluding .git, .terraform, and state files
rsync -av --progress \
  --exclude='.git' \
  --exclude='.terraform' \
  --exclude='*.tfstate' \
  --exclude='*.tfstate.*' \
  --exclude='.terraform.lock.hcl' \
  --exclude='.DS_Store' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='venv' \
  --exclude='.venv' \
  "$SOURCE/" "$DEST/"

echo "✅ Copy complete! Excluded .git, .terraform, and other build artifacts."
EOF

# Make it executable
chmod +x ~/copy-code-only.sh
```

Usage:
```bash
~/copy-code-only.sh \
  /path/to/source/Nevo-Framwork-chat-bot \
  /path/to/destination/Nevo-Framwork-chat-bot
```

---

## Fix your current situation

If you already copied the folder with `.git`:

```bash
cd /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/Nevo-Framwork-chat-bot

# Remove .git directory
rm -rf .git

# Remove .terraform directories (if any)
find . -type d -name ".terraform" -exec rm -rf {} + 2>/dev/null || true

# Remove Terraform state files
find . -name "*.tfstate" -delete
find . -name "*.tfstate.*" -delete
find . -name ".terraform.lock.hcl" -delete

# Now add to your main repo
cd /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo
git add Nevo-Framwork-chat-bot/
git commit -m "Add Nevo-Framwork-chat-bot (code only, no .git or .terraform)"
```

---

## Update `.gitignore` to prevent future issues

Ensure your root `.gitignore` excludes these:

```bash
cd /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo

# Check if .gitignore exists and add exclusions
cat >> .gitignore << 'EOF'

# Git directories (should never be copied)
**/.git/
.git/

# Terraform files
**/.terraform/
.terraform/
*.tfstate
*.tfstate.*
.terraform.lock.hcl
errored.tfstate

# Build artifacts
node_modules/
__pycache__/
*.pyc
venv/
.venv/
*.egg-info/

# OS files
.DS_Store
Thumbs.db

# IDE files
.vscode/
.idea/
*.swp
*.swo
EOF
```

---

## One-liner for quick copy (copy-paste ready)

```bash
# Copy Nevo-Framwork-chat-bot excluding .git and .terraform
rsync -av --exclude='.git' --exclude='.terraform' --exclude='*.tfstate' --exclude='*.tfstate.*' --exclude='.terraform.lock.hcl' --exclude='.DS_Store' /path/to/source/Nevo-Framwork-chat-bot/ /path/to/destination/Nevo-Framwork-chat-bot/
```

---

## What gets excluded

| Item | Why exclude |
|------|-------------|
| `.git/` | Git history (not needed when copying code) |
| `.terraform/` | Terraform plugins/cache (can be regenerated) |
| `*.tfstate` | Terraform state (contains sensitive data, should not be copied) |
| `*.tfstate.*` | Terraform backup state files |
| `.terraform.lock.hcl` | Terraform dependency lock (can be regenerated) |
| `node_modules/` | NPM packages (can be reinstalled) |
| `__pycache__/` | Python cache (can be regenerated) |
| `.DS_Store` | macOS system file (not needed) |

---

## Best practices for copying projects

1. Always exclude `.git` — you don't need Git history when copying code
2. Always exclude `.terraform` — Terraform will recreate it
3. Always exclude `*.tfstate` — contains sensitive data and should not be copied
4. Use `rsync` — easiest way to exclude multiple patterns
5. Update `.gitignore` — prevents accidentally committing these files

---

## Summary

- Problem: Copied folder includes `.git` and `.terraform` directories
- Solution: Use `rsync` with `--exclude` flags
- Quick fix: Remove `.git` and `.terraform` from already-copied folder
- Prevention: Update `.gitignore` and use the script for future copies

For your current situation:
```bash
# Remove .git from copied folder
rm -rf /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/Nevo-Framwork-chat-bot/.git

# Remove .terraform if exists
find /Users/sneha/Desktop/Sneha/Git-Hub-Action/Nevo-Demo/Nevo-Framwork-chat-bot -type d -name ".terraform" -exec rm -rf {} + 2>/dev/null || true
```

Then use `rsync` for future copies to automatically exclude these.
