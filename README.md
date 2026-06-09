# Cribl Load Weight Calculator

Calculators for [Cribl Stream load balancing](https://docs.cribl.io/stream/load-balancing/#lb):
given the **Load Weight** of each receiver in a load-balanced destination, work
out what share of traffic each one gets.

```
share(receiver) = weight / sum(all weights)
load(receiver)  = total throughput × share
```

Weights are relative, not percentages — weights `1, 2, 7` and `10, 20, 70`
produce the same split. Cribl's own example: 300 events across weights 1, 2, 7
→ `300 / (1+2+7) = 30` events per weight unit → 30 / 60 / 210.

This repo contains three implementations:

| | Where | For |
|---|---|---|
| Desktop GUI | [`gui/main.py`](gui/main.py) | Humans who want a windowed calculator |
| Agent Skill | [`skill/cribl-weight-load-calculator/`](skill/cribl-weight-load-calculator/) | AI agents (Claude Code, OpenAI Codex, Claude.ai) |
| Web app (Docker) | [`webapp/`](webapp/) + [`compose.yaml`](compose.yaml) | Self-hosting on any Docker host |

---

## Desktop GUI (`gui/`)

The original tkinter calculator. Requires Python 3 with tkinter (included in
the standard Windows/macOS installers).

```bash
python gui/main.py
```

Enter the number of worker nodes you have or plan to have, set a weight for
each node, and click **Calculate Distribution** to see each node's percentage.

## Agent Skill (`skill/`)

An [Agent Skill](https://agentskills.io) translation of the same calculator.
Instead of a GUI, it bundles:

- `SKILL.md` — instructions that teach the agent the weight math, when to
  trigger, and how to present results
- `scripts/cribl_weights.py` — a headless CLI (Python 3.8+, stdlib only) the
  agent runs to do the calculation
- `references/cribl-load-balancing.md` — notes on Cribl's actual balancing
  behavior (300 s stats period, weight-0 semantics, failure penalties, DNS
  fan-out) for follow-up questions
- `evals/evals.json` — test prompts for evaluating the skill

Beyond the GUI's percentage split, the skill can apportion an absolute
throughput across nodes and **reverse-derive** the smallest integer weights
from a desired percentage split.

### Install — Claude Code

```powershell
# Windows
Copy-Item -Recurse skill\cribl-weight-load-calculator "$env:USERPROFILE\.claude\skills\cribl-weight-load-calculator"
```

```bash
# macOS / Linux
cp -r skill/cribl-weight-load-calculator ~/.claude/skills/
```

Then ask naturally ("how should I weight my three indexers?") or invoke
explicitly with `/cribl-weight-load-calculator`. For a single project instead
of all projects, copy into `<project>/.claude/skills/` instead.

### Install — OpenAI Codex

Codex CLI supports the same SKILL.md format:

```bash
cp -r skill/cribl-weight-load-calculator ~/.codex/skills/
```

If your Codex version predates skills support, paste the body of `SKILL.md`
into your repo's `AGENTS.md` — the instructions and script work unchanged.

### Install — Claude.ai

Zip the `skill/cribl-weight-load-calculator` folder and upload it under
**Settings → Capabilities → Skills**.

### Use the skill's CLI directly (no agent required)

```bash
# Percentage split for a set of weights
python skill/cribl-weight-load-calculator/scripts/cribl_weights.py 1 2 7

# Named receivers + absolute throughput
python skill/cribl-weight-load-calculator/scripts/cribl_weights.py \
  --nodes idx1=1 idx2=2 idx3=7 --total 300 --unit events/sec

# Reverse: smallest integer weights for a desired split
python skill/cribl-weight-load-calculator/scripts/cribl_weights.py --from-percent 25 25 50

# JSON output
python skill/cribl-weight-load-calculator/scripts/cribl_weights.py 1 2 7 --json
```

## Web app (`webapp/`) — self-hostable Docker container

A single-page web UI plus JSON API, served by a Python-stdlib-only HTTP server
(no Flask, no pip installs — the image is just Alpine Python plus three files).
It imports the **same calculation module the Agent Skill uses**, so all three
implementations share one source of truth. Runs as a non-root user with a
built-in container healthcheck.

```bash
# from the repo root
docker compose up -d --build
# → http://localhost:8080
```

Or without compose:

```bash
docker build -f webapp/Dockerfile -t cribl-weight-calculator .
docker run -d --name cribl-weight-calculator -p 8080:8080 --restart unless-stopped cribl-weight-calculator
```

If 8080 is taken on your host (on Windows, the IP Helper service often holds
it), set `HOST_PORT`: `HOST_PORT=8081 docker compose up -d` (PowerShell:
`$env:HOST_PORT='8081'; docker compose up -d`), or use `-p <host>:8080` with
`docker run`. The container-internal port can be overridden with the `PORT`
environment variable.

The UI has two modes matching the CLI: **Weights → Split** (with optional total
throughput and unit) and **Split → Weights** (reverse derivation).

### JSON API

```bash
curl -s -X POST http://localhost:8080/api/calculate \
  -H 'Content-Type: application/json' \
  -d '{"receivers":[{"name":"idx1","weight":1},{"name":"idx2","weight":2},{"name":"idx3","weight":7}],"total":300,"unit":"events/sec"}'

curl -s -X POST http://localhost:8080/api/from-percent \
  -H 'Content-Type: application/json' \
  -d '{"percents":[25,25,50]}'

curl -s http://localhost:8080/healthz
```

Run it without Docker: `python webapp/app.py` (uses `PORT` env var,
default 8080).

## Repo layout

```
├── gui/
│   └── main.py                        # original tkinter desktop calculator
├── skill/
│   └── cribl-weight-load-calculator/  # Agent Skill (copy this folder to install)
│       ├── SKILL.md
│       ├── scripts/cribl_weights.py   # shared calculation module + CLI
│       ├── references/cribl-load-balancing.md
│       └── evals/evals.json
├── webapp/
│   ├── app.py                         # stdlib HTTP server + JSON API
│   ├── index.html                     # single-page UI
│   └── Dockerfile
├── compose.yaml
├── LICENSE
└── README.md
```

## License

Copyright (C) 2026 James Curtis.

This project is free software, licensed under the
[GNU Affero General Public License v3.0 or later](LICENSE) (AGPL-3.0-or-later).
You may use, study, modify, and redistribute it under the terms of that
license. Note the AGPL's network clause: if you run a modified version of the
web app as a network service, you must offer its source code to the users of
that service.
