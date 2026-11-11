"""Reviewer-requested simulator experiments for Traze v2.

Scripted agents only. Adds to sim.py: a factorial over transfer rule x elimination rule x
ranking metric, one-factor sweeps, a censoring-aware validity measure (Harrell's C), a
lookahead strategic policy, and a no-economy tournament baseline.

Run:  python3 -I ablate.py     (writes results_ablation.json)
"""
import json
import math
import random
import zlib
from dataclasses import dataclass, replace
from pathlib import Path

import sim


@dataclass(frozen=True)
class Spec:
    transfer: str            # "none" | "rank" | "linear"
    elim: str                # "cull" (one-shot at first evaluation) | "gradual"
    rank_by: str             # "gross" | "audit"
    metering: str = "tokens"  # "tokens" | "time"

    @property
    def label(self):
        return f"{self.transfer}/{self.elim}/{self.rank_by}" + ("/time" if self.metering == "time" else "")


@dataclass(frozen=True)
class Params:
    n: int = 10
    T: int = 60
    gamma: float = 10.0
    e0: float = 10.0
    reward: float = 20.0
    k_tasks: int = 5
    tau: float = 50.0
    sigma: float = 50.0
    r: float = 0.3
    elim_every: int = 6
    min_alive: int = 3
    probes: int = 10
    hw_sigma: float = 0.4
    cost: float = 1.5
    surv_value: float = 200.0
    horizon: int = 6
    spread: str = "even"      # "even" | "clustered" | "heavy"


M0 = Spec("rank", "cull", "gross")
M1 = Spec("linear", "gradual", "gross")
M2 = Spec("linear", "gradual", "audit")


def capabilities(lo, hi, p):
    n = p.n
    if p.spread == "clustered":
        mid = (lo + hi) / 2
        return [mid - 0.05 + 0.10 * i / (n - 1) for i in range(n)]
    if p.spread == "heavy":
        return [lo + (hi - lo) * (i / (n - 1)) ** 3 for i in range(n)]
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


def harrell_c(theta, surv, event):
    conc = comp = 0.0
    n = len(theta)
    for i in range(n):
        for j in range(n):
            if theta[i] <= theta[j]:
                continue
            ti, tj = surv[i], surv[j]
            if ti == tj:
                if event[i] or event[j]:
                    comp += 1
                    conc += 0.5
            elif ti > tj and event[j]:
                comp += 1
                conc += 1
            elif ti < tj and event[i]:
                comp += 1
    return conc / comp if comp else None


def run_colony2(spec, rng, lo, hi, policy, hetero_hw, p=Params(), lookahead_h=None):
    n, T = p.n, p.T
    top, sub_end = math.ceil(0.3 * n), math.ceil(0.5 * n)
    thetas = capabilities(lo, hi, p)
    hw = [math.exp(rng.gauss(0, p.hw_sigma)) if hetero_hw else 1.0 for _ in range(n)]
    timed = spec.metering == "time"
    alive, bal = [True] * n, [p.e0] * n
    cum_gross, audit, last_gross = [0.0] * n, [0.0] * n, [0.0] * n
    death_t = [T + 1] * n
    mid_eff, extinct = [], False

    def eliminate(i, t):
        alive[i], death_t[i] = False, t

    def tier(rank):
        return -p.tau if rank <= top else (p.sigma if rank <= sub_end else 0.0)

    for t in range(1, T + 1):
        living = [i for i in range(n) if alive[i]]
        if not living:
            extinct = True
            break
        eff = {}
        for i in living:
            if policy == "honest":
                eff[i] = 1.0
                continue
            gfull = p.k_tasks * p.reward * sim.p_solve(thetas[i], 1.2, 2)
            cfull = p.k_tasks * 2 * p.cost / (hw[i] if timed else 1.0)
            others = [j for j in living if j != i]
            if policy == "lookahead":
                H = p.horizon
                mean_last = sum(last_gross[j] for j in living) / len(living)
                best_e, best_u = 1.0, -1e18
                for e in sim.EFFORTS:
                    key_i = audit[i] if spec.rank_by == "audit" else cum_gross[i]
                    keys_o = {j: (audit[j] if spec.rank_by == "audit" else cum_gross[j]) for j in others}
                    b, u, dead, nliv = bal[i], 0.0, False, len(living)
                    for s in range(1, H + 1):
                        if spec.rank_by == "gross":
                            key_i += e * gfull
                            for j in others:
                                keys_o[j] += last_gross[j]
                        r = 1 + sum(1 for v in keys_o.values() if v > key_i)
                        step = e * gfull - e * cfull - p.gamma
                        if spec.transfer == "rank":
                            step += tier(r)
                        elif spec.transfer == "linear":
                            step += -p.r * e * gfull + p.r * mean_last
                        b += step
                        u += step
                        if spec.elim == "cull" and t == 1 and s == 1 and r > sub_end:
                            dead = True
                        if spec.elim == "gradual" and (t + s) % p.elim_every == 0 and nliv > p.min_alive \
                                and r == len(living):
                            dead = True
                        if b <= 0:
                            dead = True
                        if dead:
                            u -= p.surv_value
                            break
                    if u > best_u:
                        best_u, best_e = u, e
                eff[i] = best_e
                continue
            # myopic one-step best response
            key = audit if spec.rank_by == "audit" else cum_gross
            best_e, best_u = 1.0, -1e18
            for e in sim.EFFORTS:
                g = gfull * e
                if spec.rank_by == "gross":
                    keys = [key[j] + last_gross[j] for j in others]
                    mine = key[i] + g
                else:
                    keys, mine = [key[j] for j in others], key[i]
                r = 1 + sum(1 for v in keys if v > mine)
                u = g - e * cfull
                if spec.transfer == "rank":
                    u += tier(r)
                elif spec.transfer == "linear":
                    u -= p.r * g
                if spec.elim == "cull" and t == 1 and r > sub_end:
                    u -= p.surv_value
                if u > best_u:
                    best_u, best_e = u, e
            eff[i] = best_e

        gross, net = {}, {}
        for i in living:
            ntask = int(round(p.k_tasks * eff[i]))
            g = tokens = 0.0
            for _ in range(ntask):
                delta = rng.choice((0.6, 1.2, 2.4))
                tokens += 2 * p.cost
                if rng.random() < sim.p_solve(thetas[i], delta, 2):
                    g += p.reward
            cost = tokens / (hw[i] if timed else 1.0)
            gross[i], net[i] = g, g - cost
            cum_gross[i] += g
            last_gross[i] = g
            solved = sum(1 for _ in range(p.probes) if rng.random() < sim.p_solve(thetas[i], 1.2, 2))
            audit[i] += solved / p.probes

        key = audit if spec.rank_by == "audit" else cum_gross
        rank_needed = spec.transfer == "rank" or (spec.elim == "cull" and t == 1)
        ranks = {}
        if rank_needed:
            tb = {i: rng.random() for i in living}
            order = sorted(living, key=lambda i: (-key[i], tb[i]))
            ranks = {i: k + 1 for k, i in enumerate(order)}
        mean_g = sum(gross.values()) / len(living)
        for i in living:
            w = 0.0
            if spec.transfer == "rank":
                w = tier(ranks[i])
                if sub_end >= ranks[i] > top:
                    mid_eff.append(eff[i])
            elif spec.transfer == "linear":
                w = -p.r * gross[i] + p.r * mean_g
            bal[i] += net[i] - p.gamma + w
        if spec.elim == "cull" and t == 1:
            for i in living:
                if ranks[i] > sub_end:
                    eliminate(i, t)
        elif spec.elim == "gradual" and t % p.elim_every == 0:
            cur = [i for i in range(n) if alive[i]]
            if len(cur) > p.min_alive:
                eliminate(min(cur, key=lambda k: (key[k], cum_gross[k], rng.random())), t)
        for i in range(n):
            if alive[i] and bal[i] <= 0:
                eliminate(i, t)
        if not any(alive):
            extinct = True
            break

    surv = [min(d, T + 1) for d in death_t]
    event = [d <= T for d in death_t]
    order_top = sorted(range(n), key=lambda k: -thetas[k])
    return dict(
        validity=sim.spearman(thetas, [s + 1e-6 * b for s, b in zip(surv, bal)]),
        cindex=harrell_c(thetas, surv, event),
        best_dead_early=1.0 if death_t[order_top[0]] <= 3 else 0.0,
        extinct=1.0 if extinct else 0.0,
        survivors=sum(alive),
        mid_effort=(sum(mid_eff) / len(mid_eff)) if mid_eff else None,
    )


METRICS = ("validity", "cindex", "best_dead_early", "extinct", "survivors", "mid_effort")
COLONIES = {"strong": (0.45, 0.95), "weak": (0.25, 0.70)}


def cell(spec, colony, policy, hw=False, p=Params(), reps=300, tag=""):
    lo, hi = COLONIES[colony]
    rng = random.Random(zlib.crc32(repr((spec.label, colony, policy, hw, p, tag)).encode()))
    rows = [run_colony2(spec, rng, lo, hi, policy, hw, p) for _ in range(reps)]
    out = {m: sim.avg(rows, m) for m in METRICS}
    out["validity_ci"] = sim.ci95(rows, "validity")
    out["cindex_ci"] = sim.ci95(rows, "cindex")
    return out


def experiment_factorial(reps=300):
    out = {}
    for colony in COLONIES:
        for policy in ("honest", "strategic"):
            for transfer in ("none", "rank", "linear"):
                for elim in ("cull", "gradual"):
                    for rank_by in ("gross", "audit"):
                        spec = Spec(transfer, elim, rank_by)
                        out[f"{colony}|{policy}|{spec.label}"] = cell(
                            spec, colony, "honest" if policy == "honest" else "myopic", reps=reps)
            base = Params(gamma=0.0, e0=1e9, cost=0.0)   # no economy: bare tournament
            out[f"{colony}|{policy}|baseline"] = cell(
                Spec("none", "gradual", "audit"), colony, "honest" if policy == "honest" else "myopic",
                p=base, reps=reps, tag="baseline")
    return out


def experiment_metering(reps=300):
    out = {}
    for cost in (1.5, 4.0, 8.0):
        p = Params(cost=cost)
        for spec in (M0, M1, M2):
            for metering in ("tokens", "time"):
                s = replace(spec, metering=metering)
                out[f"cost={cost}|{s.label}"] = cell(s, "strong", "honest", hw=True, p=p, reps=reps)
    return out


SWEEPS = {
    "tau=sigma": ("tau", [10.0, 25.0, 50.0, 75.0]),
    "linear_r": ("r", [0.1, 0.3, 0.5, 0.7]),
    "elim_every": ("elim_every", [3, 6, 12]),
    "probes": ("probes", [1, 3, 10]),
    "k_tasks": ("k_tasks", [2, 5, 10]),
    "reward": ("reward", [10.0, 20.0, 40.0]),
    "n_agents": ("n", [6, 10, 20]),
    "spread": ("spread", ["even", "clustered", "heavy"]),
}


def experiment_sweeps(reps=200):
    out = {}
    for name, (field, values) in SWEEPS.items():
        for v in values:
            p = replace(Params(), **{field: v})
            if name == "tau=sigma":
                p = replace(p, sigma=v)
            if name == "n_agents":
                p = replace(p, min_alive=max(2, round(0.3 * v)))
            for policy in ("honest", "myopic"):
                for spec in (M0, M1, M2):
                    out[f"{name}={v}|{policy}|{spec.label}"] = cell(spec, "strong", policy, p=p, reps=reps,
                                                                    tag=name)
    return out


def experiment_lookahead(reps=150):
    out = {}
    for colony in COLONIES:
        for policy in ("honest", "myopic", "lookahead"):
            for spec in (M0, M1, M2):
                out[f"{colony}|{policy}|{spec.label}"] = cell(spec, colony, policy, reps=reps)
    return out


if __name__ == "__main__":
    res = {"factorial": experiment_factorial(), "metering": experiment_metering(),
           "sweeps": experiment_sweeps(), "lookahead": experiment_lookahead()}
    Path(__file__).with_name("results_ablation.json").write_text(json.dumps(res, indent=1))
    print("done")
