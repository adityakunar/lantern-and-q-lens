# Security

Both systems read text from the open web and pass it to a model, so the design assumes that
a fetched page may contain instructions aimed at the model.

## Keys

- Lantern reads its model key from the macOS Keychain at run time
  (`security add-generic-password -s <service> -a "$USER" -w`). Settings files hold only the
  Keychain service name.
- Q Lens uses the `ant` CLI's own sign-in. No key is stored in this repository or in the
  agent's memory store.
- `.env` files, key files and `claude-lock.json` are git-ignored. `claude-lock.json` holds the
  IDs of the resources `ant apply` creates in your workspace; they are not secrets, but they
  are yours, so they are not published here.

## What the agent can reach

- The Q Lens environment uses a limited network: the sandbox, web fetch and web search reach
  only the hosts in `q-lens/environments/q-lens-env.yml`, which is generated from the skill's
  sources. Package registries and MCP servers are blocked.
- The agent has no connectors and cannot reach your computer or your notes. It saves the
  note in its session; a script on your Mac downloads it.
- A source that moves to another site is reported, not followed. A person approves the new
  host.
- Each run has a cost cap in the deployment file.

## What Lantern can reach

- Lantern fetches only the sources in `lantern/interests/*.yaml` and sends titles and
  excerpts to the model endpoint you configure. It writes to your vault folder and its own
  library file, nowhere else.
- The note is checked in code after the model writes it: every link must be one that was
  given to the model, exactly once.

## Reporting a problem

Please open a GitHub issue for anything that is not sensitive. For a vulnerability, use
GitHub's private vulnerability reporting on this repository.
