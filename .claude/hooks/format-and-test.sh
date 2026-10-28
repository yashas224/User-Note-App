#!/usr/bin/env bash
# PostToolUse (Edit|Write): format the edited .py file, then run tests.
# Test failures exit 2 so the output is fed back to Claude.
f=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')
case "$f" in *.py) ;; *) exit 0 ;; esac

cd "$CLAUDE_PROJECT_DIR" || exit 0
uv run isort --profile black --quiet "$f"
uv run black --quiet "$f"

out=$(uv run pytest -q 2>&1)
rc=$?
# 0 = passed, 5 = no tests collected
if [ $rc -ne 0 ] && [ $rc -ne 5 ]; then
  echo "$out" | tail -40 >&2
  exit 2
fi
exit 0
