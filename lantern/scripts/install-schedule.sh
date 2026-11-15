#!/bin/bash
# Installs (or reinstalls) the weekly LaunchAgent for this checkout. --remove uninstalls it.
set -eu
label=dev.lantern.weekly
plist="$HOME/Library/LaunchAgents/$label.plist"
here="$(cd "$(dirname "$0")" && pwd)"

launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
if [ "${1:-}" = "--remove" ]; then
  rm -f "$plist"
  echo "removed $label"
  exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs/Lantern"
sed -e "s|__WEEKLY__|$here/weekly.sh|" -e "s|__HOME__|$HOME|g" \
  "$here/launchd/$label.plist" > "$plist"
plutil -lint "$plist"
launchctl bootstrap "gui/$(id -u)" "$plist"
echo "loaded $label; it runs now if this week has no note yet."
echo "check: uv run lantern status    log: ~/Library/Logs/Lantern/weekly.log"
