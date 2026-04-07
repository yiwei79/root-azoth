#!/bin/bash
# PostToolUse hook: filter verbose bash output to errors/failures only
# Prevents large test/build logs from filling context window

input=$(cat)
line_count=$(echo "$input" | wc -l)

# Only filter if output is large (>100 lines)
if [ "$line_count" -gt 100 ]; then
  filtered=$(echo "$input" | grep -iE "(error|fail|exception|traceback|assert|warning:)" -A 5 -B 1 | head -150)
  if [ -z "$filtered" ]; then
    # No errors found — emit brief success summary
    char_count=$(echo "$input" | wc -c)
    echo "[Output filtered: ${line_count} lines, ${char_count} chars — no errors detected]"
    echo "Last 10 lines:"
    echo "$input" | tail -10
  else
    echo "[Output filtered: ${line_count} lines → errors/warnings only]"
    echo "$filtered"
  fi
else
  # Small output — pass through unchanged
  echo "$input"
fi
