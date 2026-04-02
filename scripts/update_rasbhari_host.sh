#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${RASBHARI_UPDATE_REPO_DIR:?RASBHARI_UPDATE_REPO_DIR is required}"
REMOTE_NAME="${RASBHARI_UPDATE_REMOTE:-origin}"
BRANCH_NAME="${RASBHARI_UPDATE_BRANCH:-main}"
SERVICE_NAME="${RASBHARI_UPDATE_SERVICE_NAME:-rasbhari}"
HEALTHCHECK_URL="${RASBHARI_UPDATE_HEALTHCHECK_URL:-http://127.0.0.1:5000/login}"
VALIDATION_CMD="${RASBHARI_UPDATE_VALIDATION_CMD:-python3 -m py_compile server.py}"
HEALTHCHECK_ATTEMPTS="${RASBHARI_UPDATE_HEALTHCHECK_ATTEMPTS:-12}"
HEALTHCHECK_DELAY_SECONDS="${RASBHARI_UPDATE_HEALTHCHECK_DELAY_SECONDS:-5}"

cd "$REPO_DIR"

worktree_has_blocking_changes() {
  local status_line path summary_lines line
  while IFS= read -r status_line; do
    [[ -z "$status_line" ]] && continue
    if [[ "$status_line" == '?? '* ]]; then
      return 0
    fi
    path="${status_line:3}"
    [[ -z "$path" ]] && return 0

    local unstaged_summary staged_summary
    unstaged_summary="$(git diff --summary -- "$path" | sed '/^[[:space:]]*$/d')"
    staged_summary="$(git diff --cached --summary -- "$path" | sed '/^[[:space:]]*$/d')"

    if [[ -n "$unstaged_summary" || -n "$staged_summary" ]]; then
      local only_mode_change=true
      while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        [[ "$line" == *"mode change "* ]] || only_mode_change=false
      done <<< "$unstaged_summary"
      while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        [[ "$line" == *"mode change "* ]] || only_mode_change=false
      done <<< "$staged_summary"
      if [[ "$only_mode_change" == true ]]; then
        continue
      fi
    fi

    return 0
  done < <(git status --porcelain)

  return 1
}

echo "Checking repository state in $REPO_DIR"
if worktree_has_blocking_changes; then
  echo "Refusing update because the working tree is dirty."
  exit 10
fi

PREVIOUS_COMMIT="$(git rev-parse HEAD)"
echo "Current commit: $PREVIOUS_COMMIT"

git fetch "$REMOTE_NAME" "$BRANCH_NAME"
TARGET_COMMIT="$(git rev-parse FETCH_HEAD)"
echo "Target commit: $TARGET_COMMIT"

if [[ "$PREVIOUS_COMMIT" == "$TARGET_COMMIT" ]]; then
  echo "Already up to date."
  exit 0
fi

rollback() {
  echo "Rolling back to $PREVIOUS_COMMIT"
  git reset --hard "$PREVIOUS_COMMIT"
  sudo service "$SERVICE_NAME" restart
}

git checkout "$BRANCH_NAME"
git reset --hard "$TARGET_COMMIT"

echo "Running validation"
bash -lc "$VALIDATION_CMD"

echo "Restarting service $SERVICE_NAME"
sudo service "$SERVICE_NAME" restart

echo "Running health check against $HEALTHCHECK_URL"
for ((attempt=1; attempt<=HEALTHCHECK_ATTEMPTS; attempt++)); do
  if curl --silent --show-error --fail --max-time 5 "$HEALTHCHECK_URL" >/dev/null; then
    echo "Health check succeeded on attempt $attempt"
    exit 0
  fi
  sleep "$HEALTHCHECK_DELAY_SECONDS"
done

echo "Health check failed after restart"
rollback
echo "Rollback completed after failed health check"
exit 20
