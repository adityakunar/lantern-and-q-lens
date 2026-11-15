#!/usr/bin/env python3
"""Collect this week's items from the sources in sources.json, or read articles.

Prints one compact JSON line per item, newest first, so only short text reaches the
model's context. Standard library only.

    python3 collect.py --days 7 > /tmp/items.jsonl 2> /tmp/collect-summary.json
    python3 collect.py --read URL [URL ...]      # article text, for judging or writing

Self-healing (optional, state kept in the memory store between runs):

    python3 collect.py --days 7 --state /mnt/memory/q-lens-memory/source-health.json
    python3 collect.py --discover NAME --state ...   # find and verify a new feed URL on the same site
    python3 collect.py --try-fix NAME URL --state ... # verify a candidate URL and record it if it works
    python3 collect.py --days 7 --only NAME[,NAME] --state ...  # re-collect just the sources fixed this run
    python3 collect.py --suggest-move NAME URL --state ...  # source moved to another site: ask the reader

Network allowlist: when allowed-hosts.txt sits next to this script (written by
network/build-env.py with this skill's own hosts), a URL or redirect to any other host fails
fast as BlockedHost instead of a confusing 403. Such a source gets status "blocked": it is not
broken and is never quarantined; the reader decides whether to allow the host.

With --state, each source gets a status (ok, retried, fallback, stale, failed, quarantined),
verified fixes from earlier runs replace broken URLs, and the state file is updated.

Pages (sites without a feed) are read here too, with plain HTTP from the sandbox, because
the web_fetch tool only opens URLs that already appeared in the conversation.
"""
import argparse, html, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

ALLOWED_FILE = Path(__file__).with_name("allowed-hosts.txt")
ALLOWED = ({l.strip().lower() for l in ALLOWED_FILE.read_text().splitlines()
            if l.strip() and not l.startswith("#")} if ALLOWED_FILE.exists() else None)


class BlockedHost(Exception):
    """The environment's network allowlist does not include this host."""
    def __init__(self, url):
        self.url, self.host = url, (urlparse(url).hostname or "").lower()
        super().__init__(f"host not in allowlist: {self.host} ({url})")


def check_host(url):
    if ALLOWED is not None and (urlparse(url).hostname or "").lower() not in ALLOWED:
        raise BlockedHost(url)


class _CheckRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_host(newurl)  # a source that moved to a new site shows up here
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_CheckRedirects)
UA = "Mozilla/5.0 (compatible; q-lens/1.1; weekly digest)"
ATOM = "{http://www.w3.org/2005/Atom}"


def get(url, limit=6_000_000):
    check_host(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with _opener.open(req, timeout=20) as resp:
        return resp.read(limit)


def get_retry(url):
    """One retry after a short pause covers most timeouts and 5xx errors."""
    try:
        return get(url), False
    except BlockedHost:
        raise  # asking again will not help
    except Exception as exc:
        if 400 <= getattr(exc, "code", 0) < 500:
            raise  # 404 and friends will not fix themselves in 3 seconds
        time.sleep(3)
        return get(url), True


def base_domain(url):
    host = (urlparse(url).hostname or "").lower()
    parts = host.split(".")
    keep = 3 if len(parts) >= 3 and len(parts[-2]) <= 3 and len(parts[-1]) == 2 else 2  # co.uk, com.cn
    return ".".join(parts[-keep:])


def same_site(a, b):
    return base_domain(a) == base_domain(b) != ""


def parse_date(text):
    if not text:
        return None
    text = text.strip()
    for attempt in (
        lambda t: parsedate_to_datetime(t),
        lambda t: datetime.fromisoformat(t.replace("Z", "+00:00")),
        lambda t: datetime.strptime(t, "%B %d, %Y"),
        lambda t: datetime.strptime(t, "%b %d, %Y"),
    ):
        try:
            d = attempt(text)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
    return None


def clean(text, limit=400):
    text = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def parse_feed(data):
    root = ET.fromstring(data)
    items = []
    for it in root.iter("item"):  # RSS
        items.append((it.findtext("title"), it.findtext("link"),
                      parse_date(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")),
                      it.findtext("description")))
    for e in root.iter(f"{ATOM}entry"):  # Atom
        link = next((l.get("href") for l in e.findall(f"{ATOM}link") if l.get("rel") in (None, "alternate")), None)
        items.append((e.findtext(f"{ATOM}title"), link,
                      parse_date(e.findtext(f"{ATOM}published") or e.findtext(f"{ATOM}updated")),
                      e.findtext(f"{ATOM}summary") or e.findtext(f"{ATOM}content")))
    return items


def parse_page(page, data, generic=False):
    """Post links (and dates when the page shows them) from a listing page."""
    doc = data.decode("utf-8", "replace")
    base = page.get("base_url", page["url"])
    items, seen = [], set()
    if page.get("link_pattern") and not generic:
        matches = list(re.finditer(page["link_pattern"], doc))
        for n, m in enumerate(matches):
            path = m.group(1)
            if path in seen:
                continue
            seen.add(path)
            following = next((x.start() for x in matches[n + 1:] if x.group(1) != path), len(doc))
            after = doc[m.end(): min(m.end() + 1500, following)]
            date = None
            if page.get("date_pattern") and (dm := re.search(page["date_pattern"], after)):
                date = parse_date(dm.group(1))
            start, end = after.find(">"), after.find("</a>")
            title = clean(after[start + 1:end], 200) if 0 <= start < end else ""
            if not 8 <= len(title) <= 200:
                title = path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").capitalize()
            items.append((title, urljoin(base, path), date, ""))
        if page.get("order") == "numeric":
            items.sort(key=lambda i: int(re.sub(r"\D", "", i[1]) or 0), reverse=True)
        return items[: int(page.get("limit", 15))]
    # No pattern (unverified page): same-site links whose text reads like a title.
    host = urlparse(page["url"]).netloc
    for m in re.finditer(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', doc, re.S):
        url, title = urljoin(page["url"], m.group(1)), clean(m.group(2), 200)
        if urlparse(url).netloc == host and url not in seen and 15 <= len(title) <= 200:
            seen.add(url)
            items.append((title, url, None, ""))
    return items[:15]


def read_articles(urls, limit):
    for url in urls:
        try:
            doc = get(url).decode("utf-8", "replace")
            title = clean((re.search(r"<title[^>]*>(.*?)</title>", doc, re.S) or [None, ""])[1], 200)
            doc = re.sub(r"<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>", " ", doc, flags=re.S | re.I)
            body = doc[m.start():] if (m := re.search(r"<(article|main)\b", doc, re.I)) else doc
            print(json.dumps({"url": url, "title": title, "text": clean(body, limit)}, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"url": url, "error": f"{type(exc).__name__}: {exc}"[:200]}))


# ---- Self-healing state (kept in the memory store) ------------------------------------------
QUARANTINE_AFTER = 3  # failed days in a row (several runs on one day count once)   # failed runs in a row before a source counts as quarantined
STALE_DAYS = 60        # a feed with nothing newer than this is reported as stale (not a failure)


def load_state(path):
    try:
        with open(path) as f:
            state = json.load(f)
        if not isinstance(state.get("sources"), dict):
            raise ValueError("no sources map")
        return state
    except FileNotFoundError:
        return {"version": 1, "sources": {}}
    except (ValueError, json.JSONDecodeError):
        # A damaged state file never stops the run: start fresh and say so.
        print(json.dumps({"warning": f"state file {path} was unreadable; starting fresh"}), file=sys.stderr)
        return {"version": 1, "sources": {}, "reset": True}


def save_state(path, state):
    state["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def apply_fix(kind, src, state):
    """Use a verified replacement feed from an earlier run, if it is on the same site.
    Fixes are always feeds, so a page with a fix is read as a feed from then on."""
    entry = state["sources"].get(src["name"], {})
    fix = entry.get("fix_url")
    if fix and same_site(fix, src["url"]):
        return "feed", dict(src, url=fix, original_url=src["url"])
    return kind, src


def update_state(state, statuses, partial=False):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report = {"healed": [], "recovered": [], "fallback": [], "stale": [], "failed": [],
              "quarantined": [], "newly_quarantined": [], "blocked": [], "suggested_moves": []}
    if state.pop("reset", False):
        report["state_reset"] = True  # the old state file was damaged and was replaced
    for name, (status, err, src) in sorted(statuses.items()):
        e = state["sources"].setdefault(name, {})
        was_quarantined = e.get("quarantined", False)
        if status == "stale":
            e.update(failures=0, quarantined=False, last_ok=today)
            e.pop("last_error", None)
            report["stale"].append(name)
        elif status in ("ok", "retried", "fallback"):
            e.pop("blocked_host", None)
            if src.get("original_url") and not e.get("healed_reported"):
                report["healed"].append(name)
                e["healed_reported"] = True
            if was_quarantined or e.get("failures", 0):
                report["recovered"].append(name)
            e.update(failures=0, quarantined=False, last_ok=today)
            e.pop("last_error", None)
            if status == "fallback":
                report["fallback"].append(name)
        elif (err or "").startswith("BlockedHost:"):
            # Not broken: the network allowlist stops it. Never quarantined; the reader decides.
            m = re.search(r"allowlist: (\S+) \((\S+)\)", err)
            host, url = (m.group(1), m.group(2)) if m else ("?", "?")
            e.update(blocked_host=host, last_error=err[:200])
            if not same_site(url, src.get("original_url", src["url"])) and url != src["url"]:
                e.setdefault("suggested_url", url)  # it redirected to another site: likely moved
                e.setdefault("suggested_note", f"redirects to {host}, which the network blocks")
            report["blocked"].append({"source": name, "host": host, "url": url})
            status = "blocked"
        else:
            # At most one failure per day, so test runs on the same day can't quarantine a source
            # that only had one outage (W44: three runs in one afternoon quarantined Fine Arts).
            if e.get("last_failed") != today:
                e["failures"] = e.get("failures", 0) + 1
            e["last_failed"] = today
            e["last_error"] = (err or status)[:200]
            report["failed"].append(name)
            if e["failures"] >= QUARANTINE_AFTER:
                if not was_quarantined:
                    report["newly_quarantined"].append(name)
                e["quarantined"] = True
                report["quarantined"].append(name)
        e["status"] = status
        e["checked"] = today
    for name, e in sorted(state["sources"].items()):
        if e.get("suggested_url") and name in statuses and same_site(e["suggested_url"], statuses[name][2]["url"]):
            e.pop("suggested_url"); e.pop("suggested_note", None)  # the reader applied the move
        elif e.get("suggested_url") and name in statuses:
            report["suggested_moves"].append({"source": name, "url": e["suggested_url"],
                                              "note": e.get("suggested_note", "")})
    # Forget sources that are no longer in sources.json (not on an --only re-run).
    for name in list(state["sources"]) if not partial else []:
        if name not in statuses:
            del state["sources"][name]
    return report


def verify_feed_url(url, original):
    """A candidate is good if it is on the same site, parses, and has an item from the last 30 days."""
    if not same_site(url, original):
        return False, "different site"
    try:
        data = get(url)
        if re.match(rb"\s*(<!doctype html|<html)", data[:200], re.I):
            return False, "an HTML page, not a feed"
        items = parse_feed(data)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"[:120]
    dates = [d for _, _, d, _ in items if d]
    if not dates:
        return False, "no dated items"
    if max(dates) < datetime.now(timezone.utc) - timedelta(days=30):
        return False, "newest item older than 30 days"
    return True, f"{len(items)} items, newest {max(dates):%Y-%m-%d}"


def find_source(cfg, name):
    for kind in ("feeds", "pages"):
        for src in cfg.get(kind, []):
            if src["name"] == name:
                return kind, src
    sys.exit(f"unknown source: {name}")


def record_fix(state, name, url, note):
    e = state["sources"].setdefault(name, {})
    e.update(fix_url=url, fix_note=note, fix_verified=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    e.pop("healed_reported", None)


def suggest_move(cfg, state, name, url):
    """A source moved to another site. Never applied automatically (a page the agent read could
    have planted the URL): it is recorded for the reader, who approves it by changing the URL
    in the skill's sources file. Checked here only if its host is already allowed."""
    _, src = find_source(cfg, name)
    if same_site(url, src["url"]):
        return {"source": name, "suggested": None, "why": "same site: use --try-fix instead"}
    try:
        check_host(url)
        ok, why = verify_feed_url(url, url)
        why = ("works as a feed: " if ok else "checked, not a working feed: ") + why
    except BlockedHost as exc:
        why = f"not checked: {exc.host} is not in the network allowlist"
    e = state["sources"].setdefault(name, {})
    e.update(suggested_url=url, suggested_note=why[:200])
    return {"source": name, "suggested": url, "why": why}


def discover(cfg, state, name, max_probes=8):
    """Look for a working feed on the same site: <link rel=alternate> first, then usual paths."""
    _, src = find_source(cfg, name)
    original = src["url"]
    root = f"{urlparse(original).scheme}://{urlparse(original).netloc}"
    candidates = []
    for page in dict.fromkeys([original.rsplit("/", 1)[0] + "/", root + "/"]):
        try:
            doc = get(page).decode("utf-8", "replace")
            for m in re.finditer(r"<link[^>]+>", doc, re.I):
                tag = m.group(0)
                if re.search(r"rss|atom", tag, re.I) and (h := re.search(r'href="([^"]+)"', tag)):
                    candidates.append(urljoin(page, html.unescape(h.group(1))))
        except Exception:
            pass
    for path in ("/feed", "/rss.xml", "/atom.xml", "/feed.xml", "/index.xml", "/rss", "/blog/rss.xml", "/news/rss.xml"):
        candidates.append(root + path)
    tried = []
    for url in [c for c in dict.fromkeys(candidates) if c != original][:max_probes]:
        ok, why = verify_feed_url(url, original)
        tried.append({"url": url, "ok": ok, "why": why})
        if ok:
            record_fix(state, name, url, "found by discover: " + why)
            return {"source": name, "fixed": url, "tried": tried}
    return {"source": name, "fixed": None, "tried": tried}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--sources", default=str(Path(__file__).with_name("sources.json")))
    ap.add_argument("--read", nargs="+", metavar="URL", help="print the text of these articles")
    ap.add_argument("--chars", type=int, default=4000, help="characters per article with --read")
    ap.add_argument("--state", help="source health file in the memory store (enables self-healing)")
    ap.add_argument("--only", metavar="NAMES", help="comma-separated source names (re-collect just these)")
    ap.add_argument("--discover", metavar="NAME", help="find and verify a new feed URL for this source")
    ap.add_argument("--try-fix", nargs=2, metavar=("NAME", "URL"), help="verify a candidate URL and record it")
    ap.add_argument("--suggest-move", nargs=2, metavar=("NAME", "URL"),
                    help="record that a source moved to another site, for the reader to approve")
    args = ap.parse_args()
    if args.read:
        return read_articles(args.read, args.chars)
    if args.discover or args.try_fix or args.suggest_move:
        if not args.state:
            sys.exit("--discover, --try-fix and --suggest-move need --state")
        cfg, state = json.load(open(args.sources)), load_state(args.state)
        if args.suggest_move:
            result = suggest_move(cfg, state, *args.suggest_move)
        elif args.discover:
            result = discover(cfg, state, args.discover)
        else:
            name, url = args.try_fix
            _, src = find_source(cfg, name)
            ok, why = verify_feed_url(url, src["url"])
            if ok:
                record_fix(state, name, url, "try-fix: " + why)
            result = {"source": name, "fixed": url if ok else None, "why": why}
        save_state(args.state, state)
        return print(json.dumps(result))

    start = datetime.now(timezone.utc) - timedelta(days=args.days)
    cfg = json.load(open(args.sources))
    jobs = [("feed", f) for f in cfg["feeds"]] + [("page", p) for p in cfg.get("pages", [])]
    if args.only:
        wanted = set(args.only.split(","))
        jobs = [j for j in jobs if j[1]["name"] in wanted]

    state = load_state(args.state) if args.state else None
    if state is not None:
        jobs = [apply_fix(k, src, state) for k, src in jobs]

    def run(job):
        kind, src = job
        try:
            data, retried = get_retry(src["url"])
            status = "retried" if retried else "ok"
            if kind == "feed":
                items = parse_feed(data)
                dates = [d for _, _, d, _ in items if d]
                if items and dates and max(dates) < datetime.now(timezone.utc) - timedelta(days=STALE_DAYS):
                    status = "stale"  # loads, but nothing new for 60 days: maybe moved, maybe just quiet
            else:
                items = parse_page(src, data)
                if not items and src.get("link_pattern"):
                    items, status = parse_page(src, data, generic=True), "fallback"  # layout changed
            if not items:
                return kind, src, [], "failed", "no items found"
            return kind, src, items, status, None
        except Exception as exc:  # one bad source never stops the run
            return kind, src, [], "failed", f"{type(exc).__name__}: {exc}"[:200]

    out, failed, statuses = [], [], {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for kind, src, items, status, err in pool.map(run, jobs):
            statuses[src["name"]] = (status, err, src)
            if status == "failed":
                failed.append({"source": src["name"], "kind": kind, "error": err})
            for title, url, date, summary in items:
                if not url or (date and date < start):
                    continue
                if date is None and kind == "feed":
                    continue  # undated feed items are usually old
                out.append({"source": src["name"], "title": clean(title, 200), "url": url.strip(),
                            "date": date.strftime("%Y-%m-%d") if date else None,
                            "excerpt": clean(summary)})
    seen = set()
    for item in sorted(out, key=lambda i: i["date"] or "0000", reverse=True):
        if item["url"] not in seen:
            seen.add(item["url"])
            print(json.dumps(item, ensure_ascii=False))
    summary = {"sources": len(jobs), "failed": failed, "items": len(seen),
               "undated_page_links": sum(1 for i in out if not i["date"])}
    if state is not None:
        summary["health"] = update_state(state, statuses, partial=bool(args.only))
        save_state(args.state, state)
    print(json.dumps({"summary": summary}), file=sys.stderr)


if __name__ == "__main__":
    main()
