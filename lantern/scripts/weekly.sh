#!/bin/bash
# Writes this week's notes once per ISO week. launchd starts it on Monday 07:00 and every hour
# after that (scripts/launchd/dev.lantern.weekly.plist); each start exits quickly unless the
# week still needs a note, so a run missed while the Mac slept, was off or offline is retried.
# --force runs now regardless. Health goes to <state>/schedule.json for `lantern status`.
set -u

repo="$(cd "$(dirname "$0")/.." && pwd)"
state="${LANTERN_STATE:-$HOME/Library/Application Support/Lantern}"
health="$state/schedule.json"
recipes="${LANTERN_RECIPES:-ai-weekly security-weekly}"
probe="${LANTERN_PROBE_URL:-https://api.anthropic.com}"
max_attempts=6  # per week; after that it waits for --force or next week
export LANTERN_SETTINGS="${LANTERN_SETTINGS:-$HOME/.config/lantern-claude.yaml}"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

week="$(date +%G-W%V)"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
field() {  # one value from the health record; plutil on macOS, python3 elsewhere (CI)
  [ -f "$health" ] || return 1
  if command -v plutil >/dev/null; then plutil -extract "$1" raw -o - "$health" 2>/dev/null
  else python3 -c 'import json,sys; v=json.load(open(sys.argv[1])).get(sys.argv[2])
sys.exit(1) if v is None else print(v)' "$health" "$1" 2>/dev/null; fi
}

force=0
[ "${1:-}" = "--force" ] && force=1

last_week="$(field week)"
attempts=0
[ "$last_week" = "$week" ] && attempts="$(field attempts || echo 0)"
last_success="$(field last_success_week)"

# write_health STATUS DETAIL: the record `lantern status` reads.
write_health() {
  mkdir -p "$state"
  cat > "$health.tmp" <<EOF
{
  "week": "$week",
  "status": "$1",
  "detail": "$2",
  "attempts": $attempts,
  "last_attempt": "$(now)",
  "last_success": "$(if [ "$1" = ok ]; then now; else field last_success || true; fi)",
  "last_success_week": "$(if [ "$1" = ok ]; then echo "$week"; else echo "$last_success"; fi)",
  "log": "$HOME/Library/Logs/Lantern/weekly.log"
}
EOF
  mv "$health.tmp" "$health"
}

if [ $force = 0 ]; then
  [ "$last_success" = "$week" ] && exit 0                        # done this week
  [ "$(date +%u)" = 1 ] && [ "$(date +%H)" -lt 7 ] && exit 0     # before Monday 07:00
  [ "$attempts" -ge "$max_attempts" ] && exit 0                  # gave up; health says so
fi

echo "== $(now) $week attempt $((attempts + 1))"
if ! curl -sS -o /dev/null --max-time 15 "$probe"; then
  # Offline: running now would write an empty note over a good one (run 8, W44).
  write_health offline "could not reach $probe; retrying within the hour"
  echo "offline, not running"
  exit 0
fi

attempts=$((attempts + 1))
write_health running "$recipes"
cd "$repo" || { write_health failed "repo missing: $repo"; exit 1; }
failed=""
for recipe in $recipes; do  # one at a time: they share the library
  echo "-- $recipe"
  caffeinate -i uv run --locked lantern run "$recipe" || failed="$failed $recipe(exit $?)"
done

uv run --locked lantern benchmark || echo "benchmark table not updated (exit $?)"

if [ -z "$failed" ]; then
  write_health ok "$recipes"
elif [ "$attempts" -ge "$max_attempts" ]; then
  write_health gave_up "failed:$failed after $attempts attempts; run with --force"
else
  write_health failed "failed:$failed; retrying within the hour"
fi
echo "== $(now) done${failed:+, failed:$failed}"
