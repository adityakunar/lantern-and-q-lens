# Lantern: vision and core concepts

Agreed 25 Oct 2026. The north star and roadmap behind the Spec Kit specs in `specs/`.

## North star

> **Spotify for news and ideas.** Follow sources the way you follow artists, group them into
> genres, get a Discover Weekly of sources you don't follow yet, and keep everything in one
> library. The library links concepts across everything you've read, so it doubles as your
> knowledge assistant. You can turn any slice of it into a newsletter, a digest or a podcast.

## The same ideas in Spotify's terms

| Spotify | Lantern | What it is |
| --- | --- | --- |
| Artist | **Source** | Something you follow: an RSS feed, a scraped page, a podcast, a YouTube channel, a newsletter |
| Genre | **Interest** | A group of sources plus what you care about in plain words: AI, Security, Investing |
| Track | **Item** | One article, episode or post, in one standard shape |
| Your Library | **Library** | One local database of every item seen, its scores, reasons and your reactions |
| Like / Hide | **Feedback** | Ticks in your Obsidian notes, read back into the library |
| Discover Weekly | **Discovery** | Sources you don't follow, found through what your sources link to and cite, judged against your interests |
| Playlist | **Recipe** | A saved selection: which interests, time window, lens, length and format. "Weekly AI digest" is just the first recipe. |
| Lyrics / credits | **Concepts** | People, companies, ideas and products pulled out of items, which become linked notes in Obsidian |
| Podcast | **Output** | Where a recipe's result goes: an Obsidian note, a NotebookLM source pack, audio |

## The shape that stops sprawl

One small core, with three plug-in slots. Every future feature has to fit one of the slots;
if it doesn't, it waits.

```
  INPUTS (source types)          CORE                          OUTPUTS
  ─────────────────────   ┌───────────────────────┐   ─────────────────────
  RSS / Atom feed    ───► │  collect ─► Library   │ ─► Obsidian note
  Web page (scrape)  ───► │      filter ─► judge  │ ─► Obsidian concept notes
  Podcast transcript ───► │      (local model)    │ ─► NotebookLM source pack
  YouTube transcript ───► │                       │ ─► Audio overview
                          └──────────▲────────────┘
                                     │
                    RECIPES (playlists): what to select and how to write it
                    FEEDBACK: your ticks in Obsidian ─► Library
```

- **Input** = "can produce Items". Adding podcasts means adding one input, with no change to the core.
- **Recipe** = "select from the Library and write". Custom newsletters are new recipes, not new code paths.
- **Output** = "deliver what a recipe produced". NotebookLM is an output.
- **One app on top**: the Lantern app (decided 25 Oct) is an Output that reads the Library and writes back reactions. Obsidian stays as an export for notes.

## Core concepts in detail

**Source.** Types: `feed` (default, robust), `page` (best-effort scrape, e.g. The Batch), later
`podcast` and `video` (transcripts). Easy setup: `lantern add <url> --to ai` finds the feed,
previews the latest five items with dates, and adds the source.

**Interest.** One small file: sources, what you care about in plain words, and a lens.
The lens is **news** (what's new), **alerts** (does this affect me?) or **trends** (how is
this moving?). Interests differ by lens and wording, never by code.

**Item and Library.** Every collected item goes into one local database with title, link,
date, source, excerpt or transcript, and its history: seen, scored and why, written up,
your reaction. The library is what makes "no repeats", "why did I see this?" and
"what changed since last month?" possible.

**Selection.** (1) A deterministic filter: time window, not seen, not a duplicate, not
sponsored. (2) A local model judges each remaining item against the interest's
plain-words description and gives a score plus a one-line reason. Top items go in within
the budget, with a cap per source.

**Feedback.** Each item in a note carries ticks (`keep` / `less like this`). The next run
reads them back. They become examples for the judge and adjust trust in each source.

**Discovery.** Items constantly link to and cite other sources. Lantern counts the
outside sources your followed sources point to, judges a sample against your interests,
and lists the best few in a "Discover" section. Tick one to follow it.

**Concepts.** The local model tags each accepted item with a few concepts (people,
companies, techniques, products). They are written as `[[wikilinks]]` with a short
concept note per concept, so Obsidian's graph and backlinks show how ideas connect across
weeks and interests. A "knowledge assistant" then means asking questions over a vault
that is already linked, using tools that exist (Obsidian plugins, Claude with vault access,
NotebookLM) instead of building our own Q&A system.

**Recipe and Output.** A recipe = interests + window + lens + length + output. Examples:
"AI weekly" → Obsidian note; "Security alerts, daily, only tools I use" → note;
"This month in AI, 20-minute listen" → NotebookLM pack. If the local model is down, the
recipe still produces a plain list, labelled as such.

## Honest constraints to check before those stages

- **NotebookLM:** the consumer app has no general public API. There is an enterprise API in Google Cloud that I'd need to verify. The safe first version exports a source pack (markdown plus links) that you drop into a notebook. Fully automatic podcast creation depends on that API, or on a local text-to-speech model instead.
- **Spotify transcripts:** Spotify has no public transcript API. Most podcasts also publish an RSS feed with the audio, so the practical route is the podcast's feed plus a local transcription model (such as Whisper) on your Mac.
- **Scraped pages** break when sites change. The note always lists failed sources.

## Path

| Stage | Delivers |
| --- | --- |
| 1 | Core: Library, feed and page inputs, filter, local-model judge, **AI weekly note** (Obsidian, as a stopgap), weekly schedule on a self-hosted runner |
| 2 | **Lantern app**: Home, Weekly mix, Story, reactions (keep / less like this / go deeper / to Obsidian). An installable web app for any device: the Mac produces, the phone reads, offline included |
| 3 | Security and Investing interests with lenses; Genre and Artist pages; `lantern add` |
| 4 | Discover (sources your sources cite); reactions train the judge |
| 5 | Concept pages, "ask your library", trends ("what moved") |
| 6+ | Podcast and video transcript inputs; recipes such as the Monday mix; NotebookLM packs and audio |

UI mockups: https://claude.ai/artifact/MKypiFWENmhChEVKXsC1gG. Note design:
https://claude.ai/artifact/F5H5MunEguGuC23A1Y3ywr.

## Deliberately out of scope

A second UI, multiple model providers or routing, our own vector store, email.
