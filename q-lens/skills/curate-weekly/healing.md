# Healing broken sources

(Shared by every curator skill: edit it in `shared/`, never in a skill folder.)

The run should repair what it can, route around what it can't, and tell the reader both.
The skill's collector script does the mechanical part and keeps the state in the memory store
(`source-health.json` in the skill's own memory folder, `$MEM` below); you decide what to try
and write it up. The collector is `collect.py`. `<collector>` below means that script, with
the same collection options as the main run (for example `--days 7`).

## What the collector already did (no work for you)

With `--state`, each source gets a status in the `health` block of the run's summary file:

| Status | Meaning |
|---|---|
| ok | Worked. |
| retried | Failed once (timeout or server error), worked on the retry. |
| fallback | A page's link pattern found nothing (layout changed); generic link reading was used instead. Its items are rougher: judge them carefully. |
| stale | Loads, but nothing new for 60 days. Maybe moved, maybe just quiet. Not a failure. |
| failed | Did not work. `failed` in the summary has the error. |

The `health` block also lists `healed` (a fix from an earlier run worked), `recovered`,
`quarantined` (failed 3 runs in a row) and `newly_quarantined`. Fixes found in earlier runs are
applied automatically.

## What you do

1. **Try to repair each failed source**, up to the limit the skill sets. Give priority to sources
   that are not yet quarantined, then to the sources the reader cares about most (see the skill's
   interests file).
   ```bash
   python3 <collector> --discover <name> --state "$MEM/source-health.json"
   ```
   It looks for a feed on the same site, checks it works (parses, has items from the last 30
   days) and records it. Read the `tried` list if it fails: a 403 or an "HTML page" answer means
   the site blocks scripts or has no feed, and discovery won't help.

2. **If you found a likely feed URL yourself** (for example in a `web_search` result), check and
   record it the same way. Only URLs on the source's own site are accepted:
   ```bash
   python3 <collector> --try-fix <name> <url> --state "$MEM/source-health.json"
   ```

3. **Re-collect the sources you fixed**, so their items count this week:
   ```bash
   python3 <collector> <same options> --only <name>[,<name>] --state "$MEM/source-health.json" >> <items file> 2>> <summary file>
   ```

4. **Cover the gap** for a source that is still broken and matters to the reader: one
   `web_search` for `site:<its domain>` plus what the note covers (news). This
   counts toward the skill's search limit. Do this for at most 3 sources.

5. **Blocked hosts and moved sources.** The network only allows the hosts listed for the
   environment. A source whose URL or redirect leaves that list gets status `blocked` (listed
   under `blocked` in the `health` block, with the host). It is not broken and is never
   quarantined, so don't try to repair it or reach the host another way. If a source moved to
   another site (a redirect does this for you; or you saw its new home in a search result or
   on its old page), record it:
   ```bash
   python3 <collector> --suggest-move <name> <new url> --state "$MEM/source-health.json"
   ```
   Suggestions are never applied by the script. They appear under `suggested_moves` each run
   until the reader changes the URL in the skill's sources file, which also adds the new host
   to the allowlist the next time it is generated.

6. **Note what needs the reader** in `sources.md` (in `$MEM`): sources quarantined for more than
   2 runs with no fix, sources that keep landing on `fallback`, and stale sources that might be
   dead. Say what you saw and what you'd suggest changing in the skill's sources file.

## Rules

- Never edit `source-health.json` by hand; only through the collector.
- Never record a fix on another site, a mirror, or an aggregator. The script refuses them; a
  real move to another site goes through `--suggest-move`, for the reader to approve.
- Stop at the skill's limit (5 sources for the AI note). The note matters more
  than the repairs.
- A source that fails is never a reason to stop the run.

## The Health block (same in every note)

End the run report with:

```
Health
- Broke: <source (error)>, ...
- Fixed: <source: how (new URL, retry, fallback)>, ...
- Still broken: <source: how it was covered (site search, or not covered)>, ...
- Needs you: <what to change in which file>; for blocked or moved sources: "allow <host> for <source>" or "move <source> to <url>", ...
```
Write "none" for an empty line. Lantern uses the same words (ok, retried, fallback, stale,
failed, quarantined), so the two pipelines' reports can be read side by side.
