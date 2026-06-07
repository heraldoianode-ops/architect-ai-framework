#!/usr/bin/env bash
set -euo pipefail

BRANCH="claude/framework-push-script-Q9jMN"
REMOTE="origin"

echo "==> architect-ai-framework push script"

# Ensure we are on the correct branch
CURRENT=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT" != "$BRANCH" ]; then
  echo "ERROR: expected branch '$BRANCH', but currently on '$CURRENT'." >&2
  exit 1
fi

# Stage all changes
git add -A

# Only commit if there is something staged
if git diff --cached --quiet; then
  echo "Nothing to commit — working tree is clean."
else
  git commit -m "chore: update framework template

https://claude.ai/code/session_01PnC3JTUrPFWrTknnCFfRXW"
  echo "Committed."
fi

# Push with retry (exponential back-off: 2s, 4s, 8s, 16s)
MAX_RETRIES=4
DELAY=2
for attempt in $(seq 1 $((MAX_RETRIES + 1))); do
  if git push -u "$REMOTE" "$BRANCH"; then
    echo "==> Push successful."
    exit 0
  fi
  if [ "$attempt" -le "$MAX_RETRIES" ]; then
    echo "Push failed (attempt $attempt). Retrying in ${DELAY}s..."
    sleep "$DELAY"
    DELAY=$((DELAY * 2))
  fi
done

echo "ERROR: push failed after $MAX_RETRIES retries." >&2
exit 1
