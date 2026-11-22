#!/usr/bin/env python3
"""Read a Markdown (Obsidian) note aloud with Kokoro via a local rapid-mlx server.

Usage:
    python3 speak_note.py "/path/to/note.md" [--voice af_heart] [--speed 1.0]
    python3 speak_note.py --stop
    python3 speak_note.py --print note.md     # show the segments and pauses, no audio

Needs the server running:  rapid-mlx serve kokoro   (POST /v1/audio/speech)
Stdlib only. Plays with macOS `afplay`.

The note is split along its Markdown structure (headings, paragraphs, list
items, quotes, table rows). Each block is spoken on its own, followed by a
pause that fits it: long before a new section, medium after a heading or
paragraph, short between list items. Tune the PAUSES table below.
"""
import argparse
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

URL = os.environ.get("SPEAK_NOTE_URL", "http://localhost:8000/v1/audio/speech")
CHUNK_CHARS = 400
PIDFILE = os.path.join(tempfile.gettempdir(), "speak_note.pid")

# Seconds of silence AFTER each kind of block.
PAUSES = {
    "section": 1.2,    # extra silence before a new heading starts a section
    "heading": 0.7,    # after the heading itself, before its content
    "paragraph": 0.6,
    "quote": 0.6,
    "item": 0.3,       # between list items
    "list_end": 0.6,   # after the last item of a list
    "row": 0.3,        # between table rows
    "sentence": 0.1,   # between chunks of one long paragraph
}


def notify(msg):
    print(msg, file=sys.stderr)
    script = f'display notification {json.dumps(msg)} with title "Speak note"'
    subprocess.run(["osascript", "-e", script], check=False, capture_output=True)


def clean_inline(text):
    """Strip inline Markdown so only words worth hearing remain."""
    text = re.sub(r"!\[\[[^\]]*\]\]", " ", text)                      # embeds ![[...]]
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)                 # images
    text = re.sub(r"\[\[([^\]|#]*)(?:#[^\]|]*)?\|([^\]]+)\]\]", r"\2", text)  # [[a|b]] -> b
    text = re.sub(r"\[\[([^\]|#]+)(?:#[^\]]*)?\]\]", r"\1", text)     # [[a]] -> a
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)              # [text](url) -> text
    text = re.sub(r"https?://\S+", " ", text)                         # bare URLs
    text = re.sub(r"<[^>]+>", " ", text)                              # HTML tags
    text = re.sub(r"`([^`]*)`", r"\1", text)                          # inline code
    text = re.sub(r"(\*\*|__|\*|_|~~|==)(.+?)\1", r"\2", text)        # emphasis, highlights
    text = re.sub(r"(?<!\w)#[\w/-]+", " ", text)                      # #tags
    text = re.sub(r"\s+", " ", text).strip()
    return text


def end_sentence(text):
    """Give the voice a full stop so it lands the intonation."""
    return text if not text or text[-1] in ".!?:;" else text + "."


def segments(md):
    """Turn Markdown into [(text, pause_after), ...] following the note's structure."""
    md = re.sub(r"\A---\n.*?\n---\n", "", md, flags=re.S)             # YAML frontmatter
    md = re.sub(r"```.*?```", "\n", md, flags=re.S)                   # code blocks
    md = re.sub(r"%%.*?%%", " ", md, flags=re.S)                      # Obsidian comments
    md = re.sub(r"<!--.*?-->", " ", md, flags=re.S)                   # HTML comments

    blocks = []          # (kind, text)
    para = []

    def flush():
        if para:
            blocks.append(("paragraph", " ".join(para)))
            para.clear()

    for line in md.splitlines():
        s = line.strip()
        if not s or re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", s):        # blank line or rule
            flush()
            continue
        if m := re.match(r"(#{1,6})\s+(.*)", s):
            flush()
            blocks.append(("heading", m.group(2)))
        elif m := re.match(r"([-*+]|\d+[.)])\s+(\[.\]\s*)?(.*)", s):
            flush()
            blocks.append(("item", m.group(3)))
        elif s.startswith(">"):
            flush()
            callout = re.match(r"^(>\s?)+\[!", s)
            s = re.sub(r"^(>\s?)+(\[![^\]]*\][+-]?\s*)?", "", s)      # quotes, callouts
            if callout:
                s = end_sentence(s)                                   # callout title
            if blocks and blocks[-1][0] == "quote":
                blocks[-1] = ("quote", blocks[-1][1] + " " + s)
            else:
                blocks.append(("quote", s))
        elif s.startswith("|"):
            flush()
            if re.fullmatch(r"\|?[\s:|-]+\|?", s):                    # table separator row
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            blocks.append(("row", ", ".join(c for c in cells if c)))
        else:
            para.append(s)
    flush()

    out = []
    for i, (kind, raw) in enumerate(blocks):
        text = end_sentence(clean_inline(raw))
        if not re.search(r"\w", text):
            continue
        nxt = blocks[i + 1][0] if i + 1 < len(blocks) else None
        pause = PAUSES[kind]
        if kind == "item" and nxt != "item":
            pause = PAUSES["list_end"]
        if nxt == "heading" and kind != "heading":
            pause = PAUSES["section"]
        pieces = chunks(text)
        for j, piece in enumerate(pieces):
            out.append((piece, pause if j == len(pieces) - 1 else PAUSES["sentence"]))
    return out


def chunks(text, limit=CHUNK_CHARS):
    """Split a long block at sentence boundaries so each request stays short."""
    out, cur = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if cur and len(cur) + len(sent) + 1 > limit:
            out.append(cur)
            cur = ""
        cur = f"{cur} {sent}".strip()
        while len(cur) > limit:                        # one giant sentence: cut at a comma or space
            cut = max(cur.rfind(", ", 0, limit), cur.rfind(" ", 0, limit))
            cut = cut if cut > 0 else limit
            out.append(cur[:cut + 1].strip())
            cur = cur[cut + 1:].strip()
    if cur:
        out.append(cur)
    return out


def synth(text, voice, speed, path):
    body = json.dumps({"model": "kokoro", "input": text, "voice": voice,
                       "speed": speed, "response_format": "wav"}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())


def speak_note(note_path, voice="af_heart", speed=1.0):
    with open(note_path, encoding="utf-8") as f:
        parts = segments(f.read())
    if not parts:
        notify("Nothing to read in this note.")
        return
    workdir = tempfile.mkdtemp(prefix="speak_note_")
    ready = queue.Queue(maxsize=3)                     # generate ahead, but only a little

    def producer():
        try:
            for i, (text, pause) in enumerate(parts):
                wav = os.path.join(workdir, f"{i:03d}.wav")
                synth(text, voice, speed, wav)
                ready.put((wav, pause))
        except urllib.error.URLError as e:
            ready.put(e)
        ready.put(None)

    threading.Thread(target=producer, daemon=True).start()
    try:
        while (item := ready.get()) is not None:
            if isinstance(item, Exception):
                notify(f"Kokoro server not reachable at {URL}. "
                       f"Is `rapid-mlx serve kokoro` running? ({item})")
                sys.exit(1)
            wav, pause = item
            subprocess.run(["afplay", wav], check=False)
            os.remove(wav)
            time.sleep(pause / max(speed, 0.1))
    finally:
        subprocess.run(["rm", "-rf", workdir], check=False)


def stop():
    try:
        with open(PIDFILE) as f:
            os.kill(int(f.read()), 15)
    except (OSError, ValueError):
        pass
    subprocess.run(["pkill", "-x", "afplay"], check=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("note", nargs="?")
    ap.add_argument("--voice", default="af_heart")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--stop", action="store_true", help="stop whatever is playing")
    ap.add_argument("--print", action="store_true", help="only print the segments and pauses")
    a = ap.parse_args()
    if a.stop:
        stop()
        sys.exit(0)
    if not a.note:
        ap.error("give a note path, or --stop")
    if a.print:
        with open(a.note, encoding="utf-8") as f:
            for text, pause in segments(f.read()):
                print(f"[{pause:.1f}s] {text}")
        sys.exit(0)
    stop()                                             # a new note replaces the old one
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    try:
        speak_note(a.note, a.voice, a.speed)
    finally:
        if os.path.exists(PIDFILE):
            os.remove(PIDFILE)
