---
name: cribl-weight-load-calculator
description: >-
  Calculate how Cribl Stream load-balanced destinations distribute traffic across
  weighted receivers (indexers, syslog receivers, TCP/HTTP endpoints, worker
  groups). Given per-receiver Load Weight values, returns each receiver's traffic
  share as a percentage and (optionally) absolute throughput; can also
  reverse-derive the smallest integer weights that produce a desired percentage
  split. Use this whenever the user mentions Cribl load balancing, the Load
  Weight field, splitting or skewing traffic across destinations/indexers/nodes,
  "how much data will each receiver get", sizing weighted destinations, or
  sanity-checking a weight scheme — even if they never say "calculator".
compatibility: Python 3.8+ (standard library only)
---

# Cribl Weight Load Calculator

Cribl Stream load balancing sends each receiver a share of traffic proportional
to its configured **Load Weight**:

```
share(receiver) = weight / sum(all weights)
load(receiver)  = total_throughput × share(receiver)
```

Weights are relative, not percentages — weights `1, 2, 7` and `10, 20, 70`
produce identical distributions. The docs' own example: 300 events across
weights 1, 2, 7 → `300 / (1+2+7) = 30` events per weight unit → 30, 60, 210.

## Use the bundled script

Run [scripts/cribl_weights.py](scripts/cribl_weights.py) rather than computing by
hand — it validates inputs, handles rounding, and formats results consistently.

```bash
# Percentage split for a set of weights
python scripts/cribl_weights.py 1 2 7

# Named receivers + absolute throughput (any unit label you like)
python scripts/cribl_weights.py --nodes idx1=1 idx2=2 idx3=7 --total 300 --unit events/sec

# Reverse: smallest integer weights for a desired percentage split
python scripts/cribl_weights.py --from-percent 10 20 70

# Machine-readable output for further processing
python scripts/cribl_weights.py 1 2 7 --json
```

Exit code is non-zero on invalid input (negative weights, all-zero weights,
unparseable numbers), with the reason on stderr.

## Interpreting and presenting results

- Present the distribution as a table: receiver, weight, share %, and absolute
  load when the user gave a total throughput. Carry the user's unit through
  (GB/day, events/sec, EPS — the math is unit-agnostic).
- A weight of **0 is valid in Cribl but means "no connections to this
  receiver"** — the script accepts it and shows 0%. Flag it to the user, since
  a zero weight is occasionally a typo for "default" (which is 1).
- When reverse-deriving weights, prefer the smallest integer set (the script
  does this). If a requested split needs awkwardly large integers
  (e.g. 33.33/66.67), suggest the near-equivalent small ratio (1:2) and say how
  far off it is.

## What the calculation does NOT capture

Share-of-weight is the steady-state target, not an instant-by-instant
guarantee. Cribl balances against historical throughput over a stats period
(default 300 s) with decay, penalizes failing connections by 10%, and fans out
connections per worker process × resolved IPs. If the user asks why observed
traffic doesn't match the computed split, or about failover/DNS behavior, read
[references/cribl-load-balancing.md](references/cribl-load-balancing.md) before
answering.

## Worked example

User: "I have three indexers. The new one is twice the size of the old two and
we push 1.2 TB/day."

```bash
python scripts/cribl_weights.py --nodes old1=1 old2=1 new=2 --total 1.2 --unit TB/day
```

→ old1 25% (0.3 TB/day), old2 25% (0.3 TB/day), new 50% (0.6 TB/day).
Recommend setting Load Weight to 1, 1, 2 on the destination's endpoint list.
