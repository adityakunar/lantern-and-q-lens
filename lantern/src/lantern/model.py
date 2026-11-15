"""The one model endpoint: any OpenAI-compatible local server."""

from __future__ import annotations

import getpass
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from typing import Any

from .config import ModelSettings

# US dollars per million tokens (input, output) when the settings don't give a price.
# Batch and cache discounts are left out, so a figure from here is a ceiling.
KNOWN_PRICES = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
}
LOCAL_HOSTS = ("localhost", "127.0.0.1", "[::1]", "0.0.0.0")


class ModelError(Exception):
    """The model was unreachable or replied with something unusable."""


class ModelClient:
    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings
        self.name = settings.name
        self.problem: str | None = None  # why available() said no, for the run log
        self.usage = Usage()

    def _request(self, path: str, payload: dict[str, Any] | None, timeout: float) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key_env or self.settings.keychain_service:
            key = secret(self.settings.api_key_env, self.settings.keychain_service)
            headers["Authorization"] = f"Bearer {key}"
        if "api.anthropic.com" in self.settings.base_url:
            # Chat is OpenAI-compatible there, but /models is Anthropic's own API and needs this.
            headers["anthropic-version"] = "2023-06-01"
        request = urllib.request.Request(self.settings.base_url + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())
        except Exception as exc:
            raise ModelError(f"model request failed: {exc}") from exc

    def available(self) -> bool:
        try:
            listing = self._request("/models", None, 5)
        except ModelError as exc:
            # Any HTTP reply means the server is up: some servers refuse /models yet serve
            # chat. Only a refused key or no answer at all counts as unavailable.
            cause = exc.__cause__
            if isinstance(cause, urllib.error.HTTPError) and cause.code not in (401, 403):
                return True
            self.problem = str(exc)
            return False
        # A name missing from the list is a warning, not a failure: local servers often list
        # a path or alias and still answer to the configured name.
        data = listing.get("data", []) if isinstance(listing, dict) else []
        ids = [str(m.get("id")) for m in data if isinstance(m, dict)]
        if ids and self.name not in ids:
            self.problem = f"'{self.name}' is not in the server's model list ({', '.join(ids[:5])})"
        return True

    def chat(self, system: str, user: str) -> str:
        payload: dict[str, Any] = {
            "model": self.name,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if self.settings.temperature is not None:
            payload["temperature"] = self.settings.temperature
        if self.settings.max_tokens is not None:
            payload["max_tokens"] = self.settings.max_tokens
        reply = self._request("/chat/completions", payload, self.settings.timeout_s)
        self.usage.add(reply.get("usage") if isinstance(reply, dict) else None)
        try:
            return reply["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError("model reply had no message content") from exc


class Usage:
    """Tokens the server reported across a run's calls, and what they cost."""

    def __init__(self) -> None:
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.reported = True  # False once any reply came back without token counts

    def add(self, usage: Any) -> None:
        self.calls += 1
        if not isinstance(usage, dict) or "prompt_tokens" not in usage:
            self.reported = False
            return
        self.input_tokens += int(usage.get("prompt_tokens") or 0)
        self.output_tokens += int(usage.get("completion_tokens") or 0)

    def cost_usd(self, settings: ModelSettings) -> float | None:
        """List price in dollars; 0 for a model on this computer; None when unknown."""
        if not self.reported:
            return None
        if settings.price_per_mtok is not None:
            price_in, price_out = settings.price_per_mtok
        elif any(f"//{host}" in settings.base_url for host in LOCAL_HOSTS):
            return 0.0
        elif settings.name in KNOWN_PRICES:
            price_in, price_out = KNOWN_PRICES[settings.name]
        else:
            return None
        return round((self.input_tokens * price_in + self.output_tokens * price_out) / 1e6, 4)


def secret(env: str | None, service: str | None) -> str:
    """The key from the override variable if set, else from macOS Keychain; never cached."""
    if env and (value := os.environ.get(env)):
        return value
    if not service:
        raise ModelError(f"{env} is not set and no 'keychain_service' is configured")
    account = os.environ.get("USER") or getpass.getuser()
    try:
        found = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ModelError(f"could not run /usr/bin/security ({type(exc).__name__})") from None
    value = found.stdout.strip()  # never print stdout or stderr: either may hold the key
    if found.returncode != 0 or not value:
        raise ModelError(
            f"no key in macOS Keychain for service '{service}', account '{account}'; add it with:"
            f" security add-generic-password -s {service} -a \"$USER\" -w"
        )
    return value


def strip_fence(text: str) -> str:
    match = re.search(r"```(?:\w+)?\s*\n(.*?)```", text, re.S)
    return (match.group(1) if match else text).strip()


def extract_json(text: str) -> Any:
    body = strip_fence(text)
    start = min((i for i in (body.find("["), body.find("{")) if i >= 0), default=-1)
    if start < 0:
        raise ModelError("no JSON in model reply")
    try:
        return json.JSONDecoder().raw_decode(body[start:])[0]
    except json.JSONDecodeError as exc:
        raise ModelError(f"model reply was not valid JSON ({exc})") from exc
