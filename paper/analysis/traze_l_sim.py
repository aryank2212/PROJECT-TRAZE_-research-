#!/usr/bin/env python3
"""Stylized simulation of the Traze-L reference rank-tax mechanism.

This is a numerical illustration of Propositions 7-9 with scripted policies,
not a simulation of LLM behaviour. Run from the repository root:

    uv run --no-project --with numpy python paper/analysis/traze_l_sim.py
"""

from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / "paper" / "generated" / "sim_numbers.tex"

REF = dict(beta=10.0, tau=50.0, sigma=50.0, e0=10.0, horizon=60, noise=0.25, margin=5.0)


def spearman(x, y):
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    if rx.std() == 0 or ry.std() == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def simulate(theta, policy, seed, p=REF):
    """Return per-interval alive counts, colony earnings, final cumulative
    earnings E, death times and the post-culling survivor set.

    Agents earn effort * theta * (1 + noise * z) per 10-minute interval, pay a
    time burn beta, are ranked by cumulative earnings E among the living, and
    at each evaluation ranks 1-3 pay tau, ranks 4-5 receive sigma, and (at the
    first evaluation only, when ranks 6+ exist) ranks 6+ are shut down. Any
    agent whose balance is non-positive after settlement is shut down.

    policy 'greedy': full effort always.
    policy 'targeting': full effort before the culling (survival insurance);
    afterwards ranks 4-5 cap their cumulative earnings just below rank 3.
    """
    rng = np.random.default_rng(seed)
    n = len(theta)
    alive = np.ones(n, bool)
    bal = np.full(n, p["e0"])
    E = np.zeros(n)
    death = np.full(n, p["horizon"], float)
    culled = False
    survivors_after_cull = None
    alive_path, earn_path = [], []
    for t in range(p["horizon"]):
        idx = np.flatnonzero(alive)
        order = idx[np.argsort(-E[idx], kind="stable")]
        effort = np.ones(n)
        if policy == "targeting" and culled and len(order) >= 4:
            third = E[order[2]]  # rank 3's current cumulative earnings (never decreases)
            for i in order[3:5]:
                room = third - E[i] - p["margin"]
                effort[i] = np.clip(room / (theta[i] * (1 + 3 * p["noise"])), 0.0, 1.0)
        shock = np.maximum(0.0, 1 + p["noise"] * rng.standard_normal(n))
        earn = np.where(alive, effort * theta * shock, 0.0)
        E += earn
        bal += np.where(alive, earn - p["beta"], 0.0)
        idx = np.flatnonzero(alive)
        order = idx[np.argsort(-E[idx], kind="stable")]
        for pos, i in enumerate(order):
            if pos < 3:
                bal[i] -= p["tau"]
            elif pos < 5:
                bal[i] += p["sigma"]
            elif not culled:
                alive[i] = False
                death[i] = t + 1
        if not culled:
            culled = True
            survivors_after_cull = np.flatnonzero(alive)
        broke = alive & (bal <= 0)
        death[broke] = t + 1
        alive &= ~broke
        alive_path.append(int(alive.sum()))
        earn_path.append(float(earn.sum()))
    return np.array(alive_path), np.array(earn_path), E, death, survivors_after_cull


STRONG = np.linspace(30, 120, 10)
WEAK = np.linspace(10, 55, 10)


def cross_boundary_inversion(theta, E, members):
    """True if some agent ranked 4-5 (by E among members) is more capable than
    some agent ranked 1-3."""
    order = members[np.argsort(-E[members], kind="stable")]
    top, mid = order[:3], order[3:5]
    return len(mid) > 0 and theta[mid].max() > theta[top].min()


def validity(policy, runs=4000, theta=STRONG):
    """Among runs where the culling left a more capable agent in ranks 4-5 than
    some agent in ranks 1-3, the share in which that inversion is still present
    on the final leaderboard."""
    at_cull = persist = 0
    post_earn = []
    for s in range(runs):
        _, earn, E, _, surv = simulate(theta, policy, s)
        post_earn.append(earn[1:].mean())
        rng = np.random.default_rng(s)
        first = theta * np.maximum(0.0, 1 + REF["noise"] * rng.standard_normal(len(theta)))
        if cross_boundary_inversion(theta, first, surv):
            at_cull += 1
            persist += int(cross_boundary_inversion(theta, E, surv))
    return persist / max(at_cull, 1), at_cull / runs, float(np.mean(post_earn))


def survival_by_capability(theta, policy="greedy", runs=2000):
    deaths = np.array([simulate(theta, policy, s)[3] for s in range(runs)])
    return deaths.mean(axis=0)


def main():
    out = {}
    for name, theta in (("Strong", STRONG), ("Weak", WEAK)):
        a, *_ = simulate(theta, "greedy", 0)
        ext = int(np.argmax(a == 0)) + 1 if (a == 0).any() else None
        surv = survival_by_capability(theta)
        print(f"{name} colony, greedy: alive path {a[:12].tolist()} ... extinct at interval {ext}")
        print("   mean intervals survived by capability:", {int(t): round(float(d), 1) for t, d in zip(theta, surv)})
        out[f"Ext{name}"] = ext if ext is not None else "none"
        best = int(np.argmax(surv))
        out[f"Best{name}Theta"] = int(theta[best])
        out[f"Top{name}Survival"] = f"{surv[-3:].mean():.1f}"
    for policy in ("greedy", "targeting"):
        inv, cull, pe = validity(policy)
        tag = policy.capitalize()
        print(
            f"{policy:9s}: culling left a cross-boundary inversion in {cull:.3f} of runs; "
            f"it persists to the final leaderboard in {inv:.3f} of those; "
            f"colony earnings/interval after culling {pe:.1f}"
        )
        out[f"Inv{tag}"] = f"{100 * inv:.0f}"
        out[f"CullInv{tag}"] = f"{100 * cull:.0f}"
        out[f"PostEarn{tag}"] = f"{pe:.0f}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        f.write("% Generated by paper/analysis/traze_l_sim.py -- do not edit by hand.\n")
        for k, v in out.items():
            f.write(f"\\newcommand{{\\Sim{k}}}{{{v}}}\n")


if __name__ == "__main__":
    main()
