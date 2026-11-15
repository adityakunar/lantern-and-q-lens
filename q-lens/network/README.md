# Limited network for Q Lens

The agent reads web pages, so a page could try to talk it into sending data somewhere. The
environment therefore uses `networking: limited`: the sandbox, `web_fetch` and `web_search`
reach only the hosts on one list, and package registries and MCP servers stay blocked.

## How the list is built

```sh
python3 network/build-env.py           # rewrite the environment file and allowed-hosts.txt
python3 network/build-env.py --check   # exit 1 if they are out of date (run before ant apply)
python3 network/build-env.py --list    # print each host and where it comes from
```

- Every host in `skills/curate-weekly/sources*.json` (any `url` or `base_url`) is allowed.
- `extra-hosts.txt` adds the hosts that the weekly searches and redirects need, under `[news]`.
  `[all]` goes to every environment.
- Hosts match exactly: `www.example.com` is not `example.com`. Add a twin only where a site
  redirects to it.
- The API allows 128 hosts per environment. The script warns from 110.

## Adding another note

Give each note its own skill, its own environment and its own section in `extra-hosts.txt`,
and add one line to `ENVS` in `build-env.py`. Each note then reaches only its own hosts, and
no list gets near the limit.

## When a source moves

The collector never follows a source to a host that is not allowed. It reports the source as
`blocked` and suggests the move in the run report. To approve it, change the URL in the
sources file or add the host to `extra-hosts.txt`, then:

```sh
python3 network/build-env.py && ./sync-shared.sh && ant apply .
```
