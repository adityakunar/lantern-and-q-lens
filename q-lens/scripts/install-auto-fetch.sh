#!/bin/bash
# Installs (or reinstalls) the LaunchAgent that fetches new notes into the vault. --remove uninstalls it.
#
# macOS doesn't let a background job write into another app's iCloud folder (the vault lives in
# Obsidian's), so launchd starts a tiny app, "Curator Fetch", that runs scripts/auto-fetch.sh.
# The first time, macOS asks whether Curator Fetch may access data from other apps: click Allow.
# That grants only this app, not Full Disk Access. --rebuild makes a new app (macOS then asks again).
set -eu
label=dev.lantern.curator-fetch
plist="$HOME/Library/LaunchAgents/$label.plist"
here="$(cd "$(dirname "$0")" && pwd)"
app="$HOME/Applications/Curator Fetch.app"
log="$HOME/Library/Logs/Lantern/curator-fetch.log"

launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
if [ "${1:-}" = "--remove" ]; then
  rm -f "$plist"
  echo "removed $label (the app stays in ~/Applications; delete it there if you like)"
  exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs/Lantern" "$HOME/Applications"
if [ ! -d "$app" ] || [ "${1:-}" = "--rebuild" ]; then
  rm -rf "$app"
  osacompile -o "$app" -e "do shell script \"/bin/bash \" & quoted form of \"$here/auto-fetch.sh\" & \" >> \" & quoted form of \"$log\" & \" 2>&1\""
  plutil -replace LSUIElement -bool true "$app/Contents/Info.plist"          # no Dock icon
  plutil -replace CFBundleIdentifier -string "$label" "$app/Contents/Info.plist"
  codesign --force --sign - "$app"
  echo "built $app"
fi

sed -e "s|__APP__|$app/Contents/MacOS/applet|" -e "s|__HOME__|$HOME|g" \
  "$here/launchd/$label.plist" > "$plist"
plutil -lint "$plist"
launchctl bootstrap "gui/$(id -u)" "$plist"
echo "loaded $label; it checks now and then every hour."
echo "If macOS asks whether Curator Fetch may access data from other apps, click Allow."
echo "check: scripts/auto-fetch.sh --status    log: $log"
