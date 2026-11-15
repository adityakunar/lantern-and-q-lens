#!/usr/bin/env bash
# Download the newest note from the agent's latest run into your Obsidian vault.
#
#   ./fetch-latest-note.sh            # vault path read from ~/.config/lantern.yaml
#   ./fetch-latest-note.sh ~/MyVault  # or give it yourself
#
# The vault's Lantern/ folder is by topic, one subfolder per writer, each note named by its week:
#   "Lantern/AI news/Agent/2026-W45.md"
# Needs `ant` signed in (ant auth login) and curl.
set -euo pipefail

DEPLOYMENT="${DEPLOYMENT:-weekly-ai-news-digest}"
DEPLOYMENT_ID=$(DEP="$DEPLOYMENT" python3 -c 'import json,os;print(json.load(open("claude-lock.json"))["resources"]["./deployments/"+os.environ["DEP"]+".yml"]["id"])')
VAULT="${1:-$(sed -n 's/^vault:[[:space:]]*//p' ~/.config/lantern.yaml | tr -d '"'"'")}"
VAULT="${VAULT/#\~/$HOME}"
case "$DEPLOYMENT" in
  *)               TOPIC="AI news" ;;
esac
DEST="$VAULT/Lantern/$TOPIC/Agent"
[ -d "$VAULT" ] || { echo "Vault folder not found: $VAULT" >&2; exit 2; }
mkdir -p "$DEST"

SID=$(ant beta:deployment-runs list --deployment-id "$DEPLOYMENT_ID" --max-items 1 --transform session_id -r)
[ -n "$SID" ] && [ "$SID" != "null" ] || { echo "The latest run has no session (it may have failed to start)." >&2; exit 1; }
echo "Latest run: session $SID"

STATUS=$(ant beta:sessions retrieve --session-id "$SID" --transform status -r)
COST=$(ant beta:sessions retrieve --session-id "$SID" --transform usage.list_cost.amount -r || true)
echo "Status: $STATUS · cost so far: ${COST:-?} cents"
[ "$STATUS" = "running" ] && { echo "Still running; try again later." >&2; exit 1; }

SESSION_JSON=$(ant beta:sessions retrieve --session-id "$SID" --format json || true)
TOKEN=$(ant auth print-credentials --access-token)
FOUND=0
while IFS=$'\t' read -r FID NAME; do
  case "$NAME" in *.md) ;; *) continue ;; esac
  curl -fsS "https://api.anthropic.com/v1/files/$FID/content" \
    -H "Authorization: Bearer $TOKEN" \
    -H "anthropic-version: 2026-10-21" \
    -H "anthropic-beta: oauth-2025-04-20" \
    -o "$DEST/$NAME"
  # The agent names notes ai-weekly-2026-W45.md; the topic folder
  # already says which, so keep just the week.
  WEEKNAME=$(printf '%s' "$NAME" | sed -E 's/^.*([0-9]{4}-W[0-9]{2}\.md)$/\1/')
  [ "$WEEKNAME" != "$NAME" ] && mv -f "$DEST/$NAME" "$DEST/$WEEKNAME" && NAME="$WEEKNAME"
  echo "Saved $DEST/$NAME"
  # Cost and time into the note's properties, for Lantern's benchmark table (never fails the fetch).
  printf '%s' "$SESSION_JSON" | python3 "$(dirname "$0")/scripts/stamp-run-stats.py" "$DEST/$NAME" || true
  FOUND=1
done < <(ant beta:files list --scope-id "$SID" --beta managed-agents-2026-04-01 \
           --format jsonl --transform '{id,filename}' \
         | python3 -c 'import sys, json
for line in sys.stdin:
    if line.strip():
        d = json.loads(line); print(d["id"] + "\t" + d["filename"])')
[ "$FOUND" = 1 ] || { echo "No note in that run's outputs. Read the run in the Console: ant beta:sessions connect $SID --web" >&2; exit 1; }
