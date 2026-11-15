#!/usr/bin/env bash
# Copy the shared files (shared/) into every skill, so each skill uploads its own copy.
# Edit files in shared/ only; run this before `ant apply`.
#
#   ./sync-shared.sh          # copy shared/* into skills/*/ (stops if a skill copy was edited by hand)
#   ./sync-shared.sh --check  # only report differences; exit 1 if any
set -euo pipefail
cd "$(dirname "$0")"
CHECK=0; [ "${1:-}" = "--check" ] && CHECK=1
# taste.yaml (your projects + up/down-votes) is edited in Lantern; take its copy when present.
LANTERN_TASTE=../lantern/taste.yaml
if [ -f "$LANTERN_TASTE" ] && ! cmp -s "$LANTERN_TASTE" shared/taste.yaml; then
  if [ $CHECK = 1 ]; then echo "out of date: shared/taste.yaml (Lantern's copy changed)"
  else cp "$LANTERN_TASTE" shared/taste.yaml; echo "updated shared/taste.yaml from Lantern"; fi
fi
STAMP=shared/.synced          # md5 of each shared file at the last sync
touch "$STAMP"
status=0
for skill in skills/*/; do
  [ -f "$skill/SKILL.md" ] || continue
  for src in shared/*; do
    name=$(basename "$src"); dst="$skill$name"
    if [ -f "$dst" ] && cmp -s "$src" "$dst"; then continue; fi
    if [ -f "$dst" ]; then
      last=$(grep -F "  $name" "$STAMP" | awk '{print $1}' || true)
      now=$(python3 -c 'import hashlib,sys;print(hashlib.md5(open(sys.argv[1],"rb").read()).hexdigest())' "$dst")
      if [ -n "$last" ] && [ "$now" != "$last" ]; then
        echo "EDITED BY HAND: $dst differs from shared/$name. Move the change into shared/$name, then rerun." >&2
        status=1; continue
      fi
    fi
    if [ $CHECK = 1 ]; then echo "out of date: $dst"; status=1; else cp "$src" "$dst"; echo "updated $dst"; fi
  done
done
if [ $CHECK = 0 ] && [ $status = 0 ]; then
  (cd shared && for f in *; do python3 -c 'import hashlib,sys;print(hashlib.md5(open(sys.argv[1],"rb").read()).hexdigest()+"  "+sys.argv[1])' "$f"; done) > "$STAMP"
fi
[ $status = 0 ] && echo "shared files in sync"
exit $status
