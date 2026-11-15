#!/bin/bash
# Fetches each note into the Obsidian vault once its run has finished. launchd starts it every
# hour, at login and after wake (scripts/launchd/dev.lantern.curator-fetch.plist); each start
# exits quickly when there is nothing new. Remembers fetched sessions, so a note is fetched once
# and edits you make in the vault are not overwritten later.
#
#   scripts/auto-fetch.sh            # check every note now
#   scripts/auto-fetch.sh --status   # print the health record
#
# Health: ~/Library/Application Support/Lantern/curator-fetch.json
# Log:    ~/Library/Logs/Lantern/curator-fetch.log
set -u

repo="$(cd "$(dirname "$0")/.." && pwd)"
state="${CURATOR_STATE:-$HOME/Library/Application Support/Lantern}"
health="$state/curator-fetch.json"
seen="$state/curator-fetched-sessions.txt"     # one session ID per line
tries="$state/curator-fetch-tries.txt"         # "<session> <count>" for runs without a note yet
deployments="${CURATOR_DEPLOYMENTS:-weekly-ai-news-digest}"
max_tries=3                                     # per session, then it is listed under needs_you
export PATH="$HOME/.local/bin:$HOME/go/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
mkdir -p "$state"; touch "$seen" "$tries"

if [ "${1:-}" = "--status" ]; then
  cat "$health" 2>/dev/null || echo "no health record yet: $health"
  exit 0
fi

# write_health STATUS DETAIL NEEDS_YOU
write_health() {
  local last_ok
  last_ok="$(sed -n 's/.*"last_fetch": "\(.*\)".*/\1/p' "$health" 2>/dev/null)"
  [ -n "${fetched_now:-}" ] && last_ok="$(now)"
  cat > "$health.tmp" <<JSON
{
  "status": "$1",
  "detail": "$2",
  "needs_you": "$3",
  "last_check": "$(now)",
  "last_fetch": "$last_ok",
  "log": "$HOME/Library/Logs/Lantern/curator-fetch.log"
}
JSON
  mv "$health.tmp" "$health"
}

notify() {  # a macOS banner; harmless if it fails
  osascript -e "display notification \"$1\" with title \"News curator\"" >/dev/null 2>&1 || true
}

command -v ant >/dev/null || { write_health failed "ant not found on PATH ($PATH)" "install ant or fix PATH in scripts/auto-fetch.sh"; exit 1; }
if ! curl -sS -o /dev/null --max-time 15 https://api.anthropic.com; then
  write_health offline "could not reach api.anthropic.com; trying again within the hour" ""
  exit 0
fi
if ! ant auth status >/dev/null 2>&1; then
  write_health failed "ant is not signed in" "run: ant auth login"
  notify "ant is signed out: run ant auth login"
  exit 1
fi

cd "$repo" || { write_health failed "repo missing: $repo" "check the folder"; exit 1; }
# Can we write into the vault? macOS blocks background jobs from Obsidian's iCloud folder unless
# the Curator Fetch app was allowed (see scripts/install-auto-fetch.sh).
vault="$(sed -n 's/^vault:[[:space:]]*//p' ~/.config/lantern.yaml 2>/dev/null | tr -d "\"'")"
vault="${vault/#\~/$HOME}"
probe_file="$vault/Lantern/.curator-write-test"
if ! { mkdir -p "$vault/Lantern" && : > "$probe_file"; } 2>/dev/null; then
  write_health needs_you "cannot write into the vault: $vault" "allow Curator Fetch: System Settings > Privacy & Security > App Management / Files and Folders, or rerun scripts/install-auto-fetch.sh and click Allow"
  notify "Can't write to the vault: allow Curator Fetch in Privacy & Security"
  exit 1
fi
rm -f "$probe_file"
fetched_now=""; waiting=""; problems=""; needs=""
for dep in $deployments; do
  id="$(DEP="$dep" python3 -c 'import json,os;print(json.load(open("claude-lock.json"))["resources"]["./deployments/"+os.environ["DEP"]+".yml"]["id"])' 2>/dev/null)"
  [ -n "$id" ] || { problems="$problems $dep(not in claude-lock.json)"; continue; }
  sid="$(ant beta:deployment-runs list --deployment-id "$id" --max-items 1 --transform session_id -r 2>/dev/null)"
  if [ -z "$sid" ] || [ "$sid" = null ]; then continue; fi    # no run yet, or it failed to start
  grep -qx "$sid" "$seen" && continue                          # already fetched
  status="$(ant beta:sessions retrieve --session-id "$sid" --transform status -r 2>/dev/null)"
  case "$status" in
    running|rescheduling) waiting="$waiting $dep"; continue ;;
    "") problems="$problems $dep(session $sid unreadable)"; continue ;;
  esac
  echo "== $(now) $dep: session $sid is $status, fetching"
  if DEPLOYMENT="$dep" ./fetch-latest-note.sh; then
    echo "$sid" >> "$seen"
    fetched_now="$fetched_now $dep"
    notify "New note from $dep is in your vault"
  else
    prev="$(awk -v s="$sid" '$1==s{print $2}' "$tries" | tail -1)"
    n=$(( ${prev:-0} + 1 ))
    echo "$sid $n" >> "$tries"
    if [ "$n" -ge "$max_tries" ]; then
      echo "$sid" >> "$seen"     # stop retrying this session
      needs="$needs $dep: run $sid saved no note (open it: ant beta:sessions connect $sid --web);"
      notify "The $dep run saved no note"
    else
      problems="$problems $dep(fetch failed, try $n of $max_tries)"
    fi
  fi
done
# Refresh Lantern's benchmark table (<vault>/Lantern/Benchmark.md) when a note arrived.
# Lantern sits next to this repo (~/Code/projects/lantern); LANTERN_DIR overrides.
lantern="${LANTERN_DIR:-$repo/../lantern}"
if [ -n "$fetched_now" ] && [ -d "$lantern" ]; then
  (cd "$lantern" && uv run --locked lantern benchmark) || echo "benchmark table not updated"
fi
tail -n 200 "$seen" > "$seen.tmp" && mv "$seen.tmp" "$seen"
tail -n 50 "$tries" > "$tries.tmp" && mv "$tries.tmp" "$tries"

detail="fetched:${fetched_now:- none}; running:${waiting:- none}"
# Keep an earlier "needs you" until a new note arrives, so an hourly check doesn't hide it.
if [ -z "$needs$fetched_now" ] && grep -q '"status": "needs_you"' "$health" 2>/dev/null; then
  needs="$(sed -n 's/.*"needs_you": "\(.*\)".*/\1/p' "$health" 2>/dev/null)"
fi
if [ -n "$needs" ]; then write_health needs_you "$detail${problems:+; problems:$problems}" "$needs"
elif [ -n "$problems" ]; then write_health retrying "$detail; problems:$problems" ""
else write_health ok "$detail" ""
fi
[ -n "$fetched_now$problems$needs" ] && echo "== $(now) $detail${problems:+; problems:$problems}"
exit 0
