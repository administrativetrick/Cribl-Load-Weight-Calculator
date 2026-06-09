#!/usr/bin/env python3
"""Cribl Stream load-balancing weight calculator.

Computes the traffic share each load-balanced receiver gets from its
Load Weight (share = weight / sum(weights)), or reverse-derives the
smallest integer weights that produce a desired percentage split.

Examples:
    python cribl_weights.py 1 2 7
    python cribl_weights.py --nodes idx1=1 idx2=2 idx3=7 --total 300 --unit events/sec
    python cribl_weights.py --from-percent 10 20 70
    python cribl_weights.py 1 2 7 --json
"""

import argparse
import json
import sys
from fractions import Fraction
from functools import reduce
from math import gcd


def parse_weight(text, label="weight"):
    try:
        value = float(text)
    except ValueError:
        raise SystemExit(f"error: {label} '{text}' is not a number")
    if value < 0:
        raise SystemExit(f"error: {label} '{text}' is negative; Cribl Load Weights must be >= 0")
    return value


def parse_nodes(pairs):
    nodes = []
    for pair in pairs:
        name, sep, weight = pair.partition("=")
        if not sep or not name:
            raise SystemExit(f"error: expected name=weight, got '{pair}'")
        nodes.append((name, parse_weight(weight, f"weight for {name}")))
    return nodes


def distribute(nodes, total=None):
    total_weight = sum(w for _, w in nodes)
    if total_weight == 0:
        raise SystemExit("error: all weights are zero; at least one receiver needs a positive weight")
    rows = []
    for name, weight in nodes:
        share = weight / total_weight
        row = {"name": name, "weight": weight, "percent": share * 100}
        if total is not None:
            row["load"] = total * share
        rows.append(row)
    return total_weight, rows


def smallest_integer_weights(percent_strings):
    """Reduce desired percentages to the smallest exact integer weight ratio."""
    fracs = [Fraction(p) for p in percent_strings]
    if any(f < 0 for f in fracs):
        raise SystemExit("error: percentages must be >= 0")
    total = sum(fracs)
    if total == 0:
        raise SystemExit("error: percentages sum to zero")
    shares = [f / total for f in fracs]
    common = reduce(lambda a, b: a * b // gcd(a, b), (s.denominator for s in shares))
    weights = [int(s * common) for s in shares]
    divisor = reduce(gcd, weights)
    return [w // divisor for w in weights], shares


def approximate_weights(shares, max_weight=20):
    """Small-integer approximation when the exact ratio is unwieldy."""
    best = None
    for denom in range(1, max_weight + 1):
        weights = [max(round(s * denom), 0) for s in shares]
        if sum(weights) == 0:
            continue
        total = sum(weights)
        err = max(abs(w / total - float(s)) for w, s in zip(weights, shares))
        if best is None or err < best[1]:
            divisor = reduce(gcd, weights)
            best = ([w // divisor for w in weights], err)
    return best


def fmt_num(value):
    text = f"{value:,.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def print_table(rows, total_weight, total, unit):
    width = max(len(r["name"]) for r in rows + [{"name": "Total"}]) + 2
    header = f"{'Receiver':<{width}}{'Weight':>8}  {'Share':>8}"
    if total is not None:
        header += f"  {'Load':>14}  {unit or ''}"
    print(header)
    print("-" * len(header.rstrip()))
    for r in rows:
        line = f"{r['name']:<{width}}{fmt_num(r['weight']):>8}  {r['percent']:>7.2f}%"
        if total is not None:
            line += f"  {fmt_num(r['load']):>14}  {unit or ''}"
        print(line)
    footer = f"{'Total':<{width}}{fmt_num(total_weight):>8}  {'100.00%':>8}"
    if total is not None:
        footer += f"  {fmt_num(total):>14}  {unit or ''}"
    print(footer)
    zeros = [r["name"] for r in rows if r["weight"] == 0]
    if zeros:
        print(f"\nnote: weight 0 means Cribl opens NO connections to: {', '.join(zeros)}")


def main():
    parser = argparse.ArgumentParser(
        description="Cribl Stream load-balancing weight calculator",
        epilog="share = weight / sum(weights); load = total * share",
    )
    parser.add_argument("weights", nargs="*", help="receiver weights, e.g. 1 2 7")
    parser.add_argument("--nodes", nargs="+", metavar="NAME=WEIGHT",
                        help="named receivers, e.g. idx1=1 idx2=2")
    parser.add_argument("--from-percent", nargs="+", metavar="PCT", dest="from_percent",
                        help="reverse mode: derive smallest integer weights for this split")
    parser.add_argument("--total", type=float, help="total throughput to apportion")
    parser.add_argument("--unit", default="", help="unit label for --total (e.g. GB/day)")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args()

    modes = sum(bool(x) for x in (args.weights, args.nodes, args.from_percent))
    if modes != 1:
        parser.error("provide exactly one of: positional weights, --nodes, or --from-percent")

    if args.from_percent:
        weights, shares = smallest_integer_weights(args.from_percent)
        result = {
            "requested_percent": [float(s * 100) for s in shares],
            "weights": weights,
        }
        if max(weights) > 100:
            approx, err = approximate_weights(shares)
            result["approximation"] = {"weights": approx, "max_error_percent": err * 100}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Smallest exact integer weights: {':'.join(map(str, weights))}")
            if "approximation" in result:
                a = result["approximation"]
                print(f"Exact ratio is unwieldy; nearest small ratio: "
                      f"{':'.join(map(str, a['weights']))} "
                      f"(max deviation {a['max_error_percent']:.4f} pp)")
        return

    if args.nodes:
        nodes = parse_nodes(args.nodes)
    else:
        nodes = [(f"node{i + 1}", parse_weight(w)) for i, w in enumerate(args.weights)]

    total_weight, rows = distribute(nodes, args.total)

    if args.json:
        print(json.dumps({
            "total_weight": total_weight,
            "total": args.total,
            "unit": args.unit or None,
            "receivers": rows,
        }, indent=2))
    else:
        print_table(rows, total_weight, args.total, args.unit)


if __name__ == "__main__":
    main()
