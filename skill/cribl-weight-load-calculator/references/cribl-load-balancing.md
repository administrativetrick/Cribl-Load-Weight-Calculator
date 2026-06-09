# How Cribl Stream load balancing actually behaves

Distilled from https://docs.cribl.io/stream/load-balancing/ (retrieved 2026-06-09).
Read this when a user asks why observed traffic doesn't match the computed
split, or about failover, DNS, or convergence behavior.

## The weight model

- Each endpoint in a load-balanced destination has a **Load Weight**. Traffic is
  apportioned proportionally: weight 2 receives twice the data of weight 1.
- Docs example: 300 events across weights 1, 2, 7 →
  `300 / (1 + 2 + 7) = 30` events per weight unit → 30 / 60 / 210.
- **Weight 0 = no connections** to that endpoint. It is a legitimate way to
  drain a receiver, not an error.

## Why short-term traffic deviates from the computed split

- Balancing is computed against **historical throughput over a stats period
  (default 300 seconds)**, not per-event round-robin.
- At each interval, **half of the previous period's stats carry forward**
  (exponential decay). An initial 1.5:1 imbalance between equally weighted
  receivers improves to about 1.1:1 after one period and keeps converging.
  Expect the computed split to hold over minutes, not seconds.

## Failure handling

- A failed request is **resent to a different endpoint**; the destination only
  blocks when *all* endpoints are unhealthy.
- A connection failure applies a **10% penalty to that endpoint's effective
  load weight**, so a flapping receiver gets less than its configured share
  until it stabilizes.

## Connection fan-out and DNS

- Outbound connections per worker process = (# resolved IPs) × (# FQDNs).
  Total connections scale with worker process count, so per-connection
  observations can look uneven even when aggregate share matches the weights.
- Cribl recommends enabling load balancing even with a single hostname, and/or
  **round-robin DNS**, to avoid pinning all traffic to one resolved IP.

## Implications for advice

- Validate weight changes over at least one full stats period before judging.
- For draining a node, suggest weight 0 rather than removing the endpoint.
- If a user reports persistent skew, check for: flapping connections (10%
  penalties), DNS returning a single IP, or too few worker processes for the
  endpoint count.
