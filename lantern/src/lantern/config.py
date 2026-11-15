"""Load and validate settings, interests, recipes and lenses (contracts/config.md)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ConfigError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class ModelSettings:
    base_url: str
    name: str
    timeout_s: int = 120
    api_key_env: str | None = None  # variable that overrides the Keychain key when set
    keychain_service: str | None = None  # macOS Keychain generic password (account: your user)
    temperature: float | None = 0.2  # None leaves it out (newer Claude models reject other values)
    max_tokens: int | None = None  # reply cap sent with each request; None lets the server decide
    price_per_mtok: tuple[float, float] | None = None  # $ per million tokens (input, output)


@dataclass(frozen=True)
class Settings:
    vault: Path
    library: Path
    model: ModelSettings | None = None


@dataclass(frozen=True)
class Interest:
    id: str
    description: str
    themes: dict[str, list[str]]
    sources: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class Recipe:
    id: str
    interests: list[str]
    lens: str
    output: dict[str, Any]
    window_days: int = 7
    budget: int = 12
    max_stories: int = 6
    max_quick_links: int = 6
    per_source_cap: int = 3
    min_score: int = 4


@dataclass(frozen=True)
class Vote:
    points: int
    when: str


@dataclass(frozen=True)
class Taste:
    """What the reader is building, and named traits that push an item up or down."""

    building: str
    votes: dict[str, Vote]


@dataclass(frozen=True)
class Lens:
    name: str
    judge: str
    write: str


def _read_yaml(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{path}: file not found")
        return {}
    except yaml.YAMLError as exc:
        errors.append(f"{path}: not valid YAML ({exc})")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{path}: expected a mapping at the top level")
        return {}
    return data


def _unknown(path: Path, data: dict[str, Any], allowed: set[str], errors: list[str], where=""):
    for key in sorted(set(data) - allowed):
        errors.append(f"{path}: unknown key '{where}{key}'")


def load_settings(path: Path) -> Settings:
    errors: list[str] = []
    data = _read_yaml(path, errors)
    if "secrets" in data:
        errors.append(f"{path}: 'secrets' is gone; keep the key in macOS Keychain and set"
                      " 'model.keychain_service'")
    _unknown(path, data, {"vault", "library", "model", "secrets"}, errors)
    if not data.get("vault"):
        errors.append(f"{path}: 'vault' is required")
    library = data.get("library", "~/Library/Application Support/Lantern/library.sqlite")
    model = None
    if raw := data.get("model"):
        allowed = {
            "base_url", "name", "timeout_s", "api_key_env", "keychain_service", "temperature",
            "max_tokens", "price_per_mtok",
        }
        _unknown(path, raw, allowed, errors, "model.")
        temperature = raw.get("temperature", 0.2)
        if temperature is not None and (
            isinstance(temperature, bool) or not isinstance(temperature, int | float)
            or not 0 <= temperature <= 2
        ):
            errors.append(f"{path}: 'model.temperature' must be a number from 0 to 2, or null")
        max_tokens = raw.get("max_tokens")
        if max_tokens is not None and (
            isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1
        ):
            errors.append(f"{path}: 'model.max_tokens' must be a positive whole number")
        price = raw.get("price_per_mtok")
        if price is not None:
            if (not isinstance(price, dict) or set(price) != {"input", "output"} or any(
                    isinstance(v, bool) or not isinstance(v, int | float) or v < 0
                    for v in price.values())):
                errors.append(f"{path}: 'model.price_per_mtok' must be {{input: <$>, output: <$>}},"
                              " dollars per million tokens")
                price = None
            else:
                price = (float(price["input"]), float(price["output"]))
        if not raw.get("base_url") or not raw.get("name"):
            errors.append(f"{path}: 'model' needs both 'base_url' and 'name'")
        elif not errors:
            model = ModelSettings(
                str(raw["base_url"]).rstrip("/"), str(raw["name"]), int(raw.get("timeout_s", 120)),
                str(raw["api_key_env"]) if raw.get("api_key_env") else None,
                str(raw["keychain_service"]) if raw.get("keychain_service") else None,
                temperature, max_tokens, price,
            )
    if errors:
        raise ConfigError(errors)
    return Settings(Path(data["vault"]).expanduser(), Path(library).expanduser(), model)


def load_interest(root: Path, interest_id: str) -> Interest:
    from .inputs import INPUTS

    path = root / "interests" / f"{interest_id}.yaml"
    errors: list[str] = []
    data = _read_yaml(path, errors)
    if errors:
        raise ConfigError(errors)
    _unknown(path, data, {"id", "description", "themes", "sources"}, errors)
    if data.get("id") != interest_id:
        errors.append(f"{path}: 'id' must be '{interest_id}' (the file name)")
    if not str(data.get("description") or "").strip():
        errors.append(f"{path}: 'description' is required")
    themes = data.get("themes") or {}
    if not isinstance(themes, dict) or not themes:
        errors.append(f"{path}: 'themes' must list at least one theme")
        themes = {}
    sources = data.get("sources") or {}
    if not isinstance(sources, dict) or not sources:
        errors.append(f"{path}: 'sources' must list at least one source")
        sources = {}
    for name, cfg in sources.items():
        if not SLUG.match(str(name)):
            errors.append(f"{path}: source name '{name}' must be a lowercase slug")
        if not isinstance(cfg, dict):
            errors.append(f"{path}: source '{name}' must be a mapping")
            continue
        kind = cfg.get("type")
        if kind not in INPUTS:
            errors.append(f"{path}: source '{name}' has unknown type '{kind}'")
            continue
        errors += [f"{path}: source '{name}': {e}" for e in INPUTS[kind].validate(cfg)]
    if errors:
        raise ConfigError(errors)
    clean_themes = {
        str(t): [str(a).lower() for a in (aliases or [])] for t, aliases in themes.items()
    }
    return Interest(interest_id, str(data["description"]).strip(), clean_themes, sources)


def load_recipe(root: Path, recipe_id: str) -> Recipe:
    from .outputs import OUTPUTS

    path = root / "recipes" / f"{recipe_id}.yaml"
    errors: list[str] = []
    data = _read_yaml(path, errors)
    if errors:
        raise ConfigError(errors)
    fields = set(Recipe.__dataclass_fields__)
    _unknown(path, data, fields, errors)
    if data.get("id") != recipe_id:
        errors.append(f"{path}: 'id' must be '{recipe_id}' (the file name)")
    interests = data.get("interests") or []
    if len(interests) != 1:
        errors.append(f"{path}: 'interests' must name exactly one interest in stage 1")
    for key in ("window_days", "budget", "max_stories", "max_quick_links", "per_source_cap"):
        if key in data and (not isinstance(data[key], int) or data[key] < 1):
            errors.append(f"{path}: '{key}' must be a positive whole number")
    if not 1 <= int(data.get("window_days", 7)) <= 31:
        errors.append(f"{path}: 'window_days' must be between 1 and 31")
    if not (root / "lenses" / f"{data.get('lens')}.md").exists():
        errors.append(f"{path}: lens '{data.get('lens')}' has no file in lenses/")
    output = data.get("output") or {}
    if output.get("type") not in OUTPUTS:
        errors.append(f"{path}: output type '{output.get('type')}' is not available")
    else:
        errors += [f"{path}: output: {e}" for e in OUTPUTS[output["type"]].validate(output)]
    if errors:
        raise ConfigError(errors)
    return Recipe(**{k: v for k, v in data.items() if k in fields})


def load_taste(root: Path) -> Taste | None:
    """taste.yaml at the config root; optional, so a root without one judges as before."""
    path = root / "taste.yaml"
    if not path.exists():
        return None
    errors: list[str] = []
    data = _read_yaml(path, errors)
    if errors:
        raise ConfigError(errors)
    _unknown(path, data, {"building", "votes"}, errors)
    votes: dict[str, Vote] = {}
    raw = data.get("votes") or {}
    if not isinstance(raw, dict):
        errors.append(f"{path}: 'votes' must be a mapping of vote ids")
        raw = {}
    for vid, cfg in raw.items():
        if not SLUG.match(str(vid)):
            errors.append(f"{path}: vote '{vid}' must be a lowercase slug")
            continue
        if not isinstance(cfg, dict):
            errors.append(f"{path}: vote '{vid}' must be a mapping")
            continue
        _unknown(path, cfg, {"points", "when"}, errors, where=f"votes.{vid}.")
        points, when = cfg.get("points"), str(cfg.get("when") or "").strip()
        if not isinstance(points, int) or isinstance(points, bool) or not -5 <= points <= 5:
            errors.append(f"{path}: vote '{vid}': 'points' must be a whole number from -5 to 5")
        if not when:
            errors.append(f"{path}: vote '{vid}': 'when' is required")
        if not errors:
            votes[str(vid)] = Vote(points, when)
    if errors:
        raise ConfigError(errors)
    return Taste(str(data.get("building") or "").strip(), votes)


def load_lens(root: Path, name: str) -> Lens:
    text = (root / "lenses" / f"{name}.md").read_text(encoding="utf-8")
    sections = dict(
        (m.group(1).strip().lower(), m.group(2).strip())
        # Only these two headings split the file, so the Write section may show "## …" lines.
        for m in re.finditer(
            r"^## (Judge|Write)[ \t]*\n(.*?)(?=^## (?:Judge|Write)[ \t]*$|\Z)", text, re.M | re.S
        )
    )
    missing = [s for s in ("judge", "write") if s not in sections]
    if missing:
        raise ConfigError([f"lenses/{name}.md: missing section(s) {', '.join(missing)}"])
    return Lens(name, sections["judge"], sections["write"])
