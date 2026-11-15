# Contract: Input, Recipe and Output slots

The core never imports a specific Input or Output; it looks them up by `type` in a registry.

## Input

```python
class Input(Protocol):
    type: str                                   # "feed", "page"
    def validate(self, cfg: dict) -> list[str]  # config errors, empty if valid
    def collect(self, name: str, cfg: dict, fetch: Fetch) -> list[Item]
```

- `fetch(url) -> bytes` is injected (real `net.get` or the test fake); Inputs never open
  sockets themselves.
- Must raise `SourceError(reason)` for a failed source; the core records it and continues.
- Must return Items in the common shape; must not filter by date or seen state.

## Recipe

Data, not code: a recipe file plus a lens file ([config.md](config.md)). The core's
`run(recipe)` is the only recipe executor. A new recipe = new YAML (and optionally a new lens).

## Output

```python
class Output(Protocol):
    type: str                                   # "obsidian"
    def validate(self, cfg: dict, settings: Settings) -> list[str]
    def deliver(self, note: RenderedNote, cfg: dict, settings: Settings) -> str  # returns location
```

- `RenderedNote` = frontmatter dict + Markdown body + period + note id.
- Must be idempotent per note id (rerun replaces).

## Contract tests

Each registered Input and Output has a contract test run against fixtures; adding a new one
means adding it to the registry and to the parametrised contract tests.
