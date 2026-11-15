from pathlib import Path

import pytest

from lantern.config import ConfigError, load_interest, load_lens, load_recipe, load_settings

REPO = Path(__file__).parents[2]


def test_shipped_config_loads():
    interest = load_interest(REPO, "ai")
    feeds = [s for s in interest.sources.values() if s["type"] == "feed"]
    assert len(feeds) == 53 and len(interest.sources) == 64 and len(interest.themes) == 20
    recipe = load_recipe(REPO, "ai-weekly")
    assert recipe.output == {"type": "obsidian", "folder": "Lantern/AI news/Lantern"}
    security = load_interest(REPO, "security")
    assert "ai-security" in security.themes and len(security.sources) == 13
    assert load_recipe(REPO, "security-weekly").output["folder"] == "Lantern/Security/Lantern"
    lens = load_lens(REPO, "news")
    assert "Score each article" in lens.judge and "## Also worth a look" in lens.write


def test_every_problem_is_reported(tmp_path):
    (tmp_path / "interests").mkdir()
    (tmp_path / "interests" / "x.yaml").write_text(
        "id: y\nthemes: {a: []}\nsources:\n  Bad Name: {type: rss}\n"
        "  ok: {type: feed, url: ftp://x, colour: red}\n"
    )
    with pytest.raises(ConfigError) as err:
        load_interest(tmp_path, "x")
    text = str(err.value)
    for expected in ("'id' must be 'x'", "'description' is required", "lowercase slug",
                     "unknown type 'rss'", "unknown key 'colour'", "http(s)"):
        assert expected in text


def test_recipe_output_folder_stays_in_the_vault(tmp_path):
    (tmp_path / "recipes").mkdir()
    (tmp_path / "lenses").mkdir()
    (tmp_path / "lenses" / "news.md").write_text("## Judge\nj\n## Write\nw\n")
    (tmp_path / "recipes" / "r.yaml").write_text(
        "id: r\ninterests: [ai]\nlens: news\nbudgt: 3\noutput: {type: obsidian, folder: ../out}\n"
    )
    with pytest.raises(ConfigError) as err:
        load_recipe(tmp_path, "r")
    assert "unknown key 'budgt'" in str(err.value) and "inside the vault" in str(err.value)


def test_settings(tmp_path):
    path = tmp_path / "lantern.yaml"
    path.write_text("vault: ~/v\nmodel: {base_url: 'http://h:9/v1/', name: m}\n")
    settings = load_settings(path)
    assert settings.model.base_url == "http://h:9/v1" and settings.vault.is_absolute()
    path.write_text("model: {name: m}\n")
    with pytest.raises(ConfigError, match="vault"):
        load_settings(path)


def test_model_api_key_env(tmp_path, monkeypatch):
    from lantern.model import ModelClient, ModelError
    path = tmp_path / "lantern.yaml"
    path.write_text("vault: ~/v\nmodel: {base_url: 'https://c.test/v1', name: m,"
                    " api_key_env: LANTERN_TEST_KEY}\n")
    settings = load_settings(path)
    assert settings.model.api_key_env == "LANTERN_TEST_KEY"
    monkeypatch.delenv("LANTERN_TEST_KEY", raising=False)
    with pytest.raises(ModelError, match="LANTERN_TEST_KEY is not set"):
        ModelClient(settings.model).chat("s", "u")


def _fake_keychain(monkeypatch, store):
    import subprocess
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        service, account = args[args.index("-s") + 1], args[args.index("-a") + 1]
        value = store.get((service, account))
        return subprocess.CompletedProcess(args, 0 if value else 44, (value or "") + "\n", "")

    monkeypatch.setattr(subprocess, "run", run)
    return calls


def test_secret_from_keychain(tmp_path, monkeypatch):
    from lantern.model import ModelError, secret
    monkeypatch.setenv("USER", "q")
    monkeypatch.delenv("LANTERN_TEST_KEY", raising=False)
    calls = _fake_keychain(monkeypatch, {("anthropic", "q"): "from-keychain"})
    assert secret("LANTERN_TEST_KEY", "anthropic") == "from-keychain"
    assert secret(None, "anthropic") == "from-keychain"
    assert calls[0] == [
        "/usr/bin/security", "find-generic-password", "-s", "anthropic", "-a", "q", "-w"
    ]
    monkeypatch.setenv("LANTERN_TEST_KEY", "from-env")
    assert secret("LANTERN_TEST_KEY", "anthropic") == "from-env"  # the variable overrides
    with pytest.raises(ModelError, match="security add-generic-password -s nvidia"):
        secret(None, "nvidia")


def test_settings_keychain_service(tmp_path, monkeypatch):
    from lantern import model as model_module
    from lantern.model import ModelClient
    path = tmp_path / "lantern.yaml"
    path.write_text("vault: ~/v\nmodel: {base_url: 'https://c.test/v1', name: m,"
                    " keychain_service: nvidia}\n")
    settings = load_settings(path)
    assert settings.model.keychain_service == "nvidia" and settings.model.api_key_env is None
    monkeypatch.setenv("USER", "q")
    _fake_keychain(monkeypatch, {("nvidia", "q"): "k"})
    seen = []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"choices": [{"message": {"content": "ok"}}]}'

    monkeypatch.setattr(model_module.urllib.request, "urlopen",
                        lambda req, timeout: seen.append(req.headers) or Reply())
    assert ModelClient(settings.model).chat("s", "u") == "ok"
    assert seen[0]["Authorization"] == "Bearer k"
    path.write_text("vault: ~/v\nsecrets: ~/.config/lantern/secrets.env\n")
    with pytest.raises(ConfigError, match="Keychain"):
        load_settings(path)


def test_model_temperature_and_max_tokens(tmp_path, monkeypatch):
    from lantern import model as model_module
    from lantern.model import ModelClient
    path = tmp_path / "lantern.yaml"
    path.write_text("vault: ~/v\nmodel: {base_url: 'http://h:9/v1', name: m}\n")
    default = load_settings(path).model
    assert default.temperature == 0.2 and default.max_tokens is None
    path.write_text("vault: ~/v\nmodel: {base_url: 'https://api.anthropic.com/v1',"
                    " name: claude-sonnet-5-5, temperature: null, max_tokens: 16000}\n")
    claude = load_settings(path).model
    assert claude.temperature is None and claude.max_tokens == 16000
    sent = []
    monkeypatch.setattr(model_module.ModelClient, "_request",
                        lambda self, p, payload, t: sent.append(payload)
                        or {"choices": [{"message": {"content": "ok"}}]})
    assert ModelClient(claude).chat("s", "u") == "ok"
    assert "temperature" not in sent[0] and sent[0]["max_tokens"] == 16000
    ModelClient(default).chat("s", "u")
    assert sent[1]["temperature"] == 0.2 and "max_tokens" not in sent[1]
    for bad in ("temperature: hot", "temperature: 3", "max_tokens: 0", "max_tokens: true"):
        path.write_text(f"vault: ~/v\nmodel: {{base_url: 'http://h:9/v1', name: m, {bad}}}\n")
        with pytest.raises(ConfigError, match=bad.split(":")[0]):
            load_settings(path)


def test_model_available_counts_any_http_reply(tmp_path, monkeypatch):
    import urllib.error

    from lantern import model as model_module
    from lantern.model import ModelClient
    path = tmp_path / "lantern.yaml"
    path.write_text("vault: ~/v\nmodel: {base_url: 'http://h:9/v1', name: m}\n")
    settings = load_settings(path).model

    def answer(error):
        def urlopen(request, timeout):
            raise error
        monkeypatch.setattr(model_module.urllib.request, "urlopen", urlopen)
        client = ModelClient(settings)
        return client.available(), client.problem

    http = lambda code: urllib.error.HTTPError("http://h:9/v1/models", code, "x", {}, None)  # noqa: E731
    assert answer(http(400)) == (True, None)  # Anthropic refuses /models but serves chat
    up, problem = answer(http(401))
    assert not up and "401" in problem
    up, problem = answer(urllib.error.URLError("Connection refused"))
    assert not up and "Connection refused" in problem


def test_anthropic_requests_carry_the_api_version(tmp_path, monkeypatch):
    from lantern import model as model_module
    from lantern.model import ModelClient
    path = tmp_path / "lantern.yaml"
    sent = []

    def urlopen(request, timeout):
        sent.append(request.get_header("Anthropic-version"))
        raise model_module.urllib.error.URLError("stop")
    monkeypatch.setattr(model_module.urllib.request, "urlopen", urlopen)
    for base in ("https://api.anthropic.com/v1", "http://h:9/v1"):
        path.write_text(f"vault: ~/v\nmodel: {{base_url: '{base}', name: m}}\n")
        ModelClient(load_settings(path).model).available()
    assert sent == ["2023-06-01", None]


def test_model_name_missing_from_the_list_is_a_warning(tmp_path, monkeypatch):
    from lantern import model as model_module
    from lantern.model import ModelClient
    path = tmp_path / "lantern.yaml"
    path.write_text("vault: ~/v\nmodel: {base_url: 'http://h:9/v1', name: m}\n")
    settings = load_settings(path).model
    for ids, problem in ((["m", "n"], None), (["n"], "'m' is not in the server's model list (n)"),
                         ([], None)):
        monkeypatch.setattr(model_module.ModelClient, "_request",
                            lambda self, p, payload, t, ids=ids: {"data": [{"id": i} for i in ids]})
        client = ModelClient(settings)
        assert client.available() and client.problem == problem


def test_usage_cost(tmp_path):
    from lantern.config import ModelSettings
    from lantern.model import Usage

    usage = Usage()
    usage.add({"prompt_tokens": 1_000_000, "completion_tokens": 100_000})
    assert usage.cost_usd(ModelSettings("https://api.anthropic.com/v1", "claude-opus-5-5")) == 6.0
    assert usage.cost_usd(ModelSettings("http://localhost:8000/v1", "qwen")) == 0.0
    assert usage.cost_usd(ModelSettings("https://x.test/v1", "mystery")) is None
    assert usage.cost_usd(ModelSettings("https://x.test/v1", "m", price_per_mtok=(1, 1))) == 1.1
    usage.add(None)  # a server that sends no counts makes the total unknown, not low
    assert usage.cost_usd(ModelSettings("https://api.anthropic.com/v1", "claude-opus-5-5")) is None
    path = tmp_path / "lantern.yaml"
    path.write_text("vault: ~/v\nmodel: {base_url: 'http://h/v1', name: m,"
                    " price_per_mtok: {input: 2, output: 10}}\n")
    assert load_settings(path).model.price_per_mtok == (2.0, 10.0)
    path.write_text("vault: ~/v\nmodel: {base_url: 'http://h/v1', name: m, price_per_mtok: 3}\n")
    with pytest.raises(ConfigError, match="price_per_mtok"):
        load_settings(path)


def test_taste_is_optional_and_validated(tmp_path):
    from lantern.config import ConfigError, load_taste

    assert load_taste(tmp_path) is None
    (tmp_path / "taste.yaml").write_text(
        "building: Lantern\nvotes:\n  own_stack: {points: 2, when: Changes a project}\n"
    )
    taste = load_taste(tmp_path)
    assert taste.building == "Lantern" and taste.votes["own_stack"].points == 2
    (tmp_path / "taste.yaml").write_text("votes:\n  Bad: {points: 9}\n  ok: {points: 1}\n")
    try:
        load_taste(tmp_path)
    except ConfigError as exc:
        assert any("lowercase slug" in e for e in exc.errors)
        assert any("vote 'ok': 'when' is required" in e for e in exc.errors)
    else:
        raise AssertionError


def test_repo_taste_loads():
    from pathlib import Path

    from lantern.config import load_taste

    taste = load_taste(Path(__file__).resolve().parents[2])
    assert taste is not None and "own_stack" in taste.votes
