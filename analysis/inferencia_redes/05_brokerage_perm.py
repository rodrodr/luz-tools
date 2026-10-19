"""Permutation test for the Gould-Fernandez brokerage roles of brokerage_roles().

Gould and Fernandez's z compares each count with a random network of the same density, every tie
independent: it does not hold degrees fixed and ignores reciprocity. Here the network stays as it is
(so every deputy keeps the ties they have) and only the group labels are shuffled among the members:
does the support network route brokerage through groups more (or less) than the same network with
labels at random would?

    results/brokerage_perm.csv           chamber totals per role: observed, null mean and sd, z, p
    results/brokerage_perm_groups.csv    the same per group (the broker's group)

Run from the repository root: .venv/bin/python analysis/inferencia_redes/05_brokerage_perm.py [perms]
"""
import csv
import random
import statistics
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from luz_mcp import groups as G, profile  # noqa: F401  (activates the Luz profile)

HERE = Path(__file__).resolve().parent
LEGS = ("1931-1933", "1933-1936", "1936-1939")
BYS = ("party", "family")


def totals(net, by) -> tuple[Counter, Counter]:
    """Chamber totals per role, and per (broker's group, role)."""
    glob, per = Counter(), Counter()
    for b, n in G._gf_counts(net, by).items():
        g = G._label(net, b, by)
        for r, k in n.items():
            glob[r] += k
            per[(g, r)] += k
    return glob, per


def run(task):
    leg, by, perms, seed = task
    net = G._network(leg)
    key = G.GROUP_KEYS[by]
    obs_g, obs_p = totals(net, by)
    members = net["members"]
    labels = [net["attrs"][x].get(key) for x in members]
    rng = random.Random(seed)
    null_g, null_p = {r: [] for r in G.ROLES}, {}
    for _ in range(perms):
        shuffled = labels[:]
        rng.shuffle(shuffled)
        attrs = {x: {**net["attrs"][x], key: lab} for x, lab in zip(members, shuffled)}
        g, p = totals({**net, "attrs": attrs}, by)
        for r in G.ROLES:
            null_g[r].append(g[r])
        for k in set(p) | set(obs_p):
            null_p.setdefault(k, []).append(p[k])
    for k in null_p:  # groups/roles absent from some permutations count 0 there
        null_p[k] += [0] * (perms - len(null_p[k]))

    def row(obs, null):
        m, s = statistics.fmean(null), statistics.pstdev(null)
        return {"observed": obs, "null_mean": round(m, 1), "null_sd": round(s, 1),
                "ratio": round(obs / m, 3) if m else None, "z_perm": round((obs - m) / s, 2) if s else None,
                "p_greater": round((sum(v >= obs for v in null) + 1) / (perms + 1), 4),
                "p_less": round((sum(v <= obs for v in null) + 1) / (perms + 1), 4)}
    chamber = [{"legislature": leg, "by": by, "role": r, **row(obs_g[r], null_g[r]), "perms": perms} for r in G.ROLES]
    groups = [{"legislature": leg, "by": by, "group": g, "role": r, **row(obs_p.get((g, r), 0), null_p[(g, r)]),
               "perms": perms} for (g, r) in sorted(null_p)]
    return chamber, groups


def main() -> None:
    perms = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    tasks = [(leg, by, perms, 1000 + k) for k, (leg, by) in enumerate((l, b) for l in LEGS for b in BYS)]
    with ProcessPoolExecutor(max_workers=6) as ex:
        out = list(ex.map(run, tasks))
    for name, rows in (("brokerage_perm.csv", [r for c, _ in out for r in c]),
                       ("brokerage_perm_groups.csv", [r for _, g in out for r in g])):
        with open(HERE / "results" / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    for c, _ in out:
        for r in c:
            print(r["legislature"], r["by"], r["role"], r["observed"], r["null_mean"], r["z_perm"], r["p_greater"],
                  r["p_less"])


if __name__ == "__main__":
    main()
