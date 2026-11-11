"""Traze v2 mechanism simulator.

Scripted agents (NOT language models) compete in a survival economy under four
mechanisms. The aim is to test properties of the *rules*: does survival track
capability, do agents game the schedule, does the colony go extinct.

Run:  python3 -I sim.py   (writes results.json next to this file)
"""
import json
import math
import zlib
import random
from pathlib import Path

N = 10            # agents per colony
T = 60            # intervals (10 hours of 10-minute intervals)
GAMMA = 10.0      # time burn per interval
E0 = 10.0         # initial endowment
REWARD = 20.0     # compute earned per solved task
TAU, SIGMA = 50.0, 50.0   # reference rank tax / subsidy
K_TASKS = 5       # tasks attempted per interval at full effort
EFFORTS = (0.0, 0.5, 1.0)
SURVIVAL_VALUE = 200.0    # myopic value an agent puts on not being eliminated
HW_SIGMA = 0.4            # lognormal spread of hardware throughput


def p_solve(theta, delta, depth):
    """Success probability: deeper reasoning helps, harder tasks hurt."""
    return theta ** (delta / math.sqrt(depth))


def best_depth(theta, delta, cost_per_depth):
    best, best_v = 1, -1e9
    for d in (1, 2, 3, 4):
        v = REWARD * p_solve(theta, delta, d) - cost_per_depth * d
        if v > best_v:
            best, best_v = d, v
    return best


class Mech:
    def __init__(self, name, rank_tax, time_metered, linear_r, gradual, audit_rank):
        self.name, self.rank_tax, self.time_metered = name, rank_tax, time_metered
        self.linear_r, self.gradual, self.audit_rank = linear_r, gradual, audit_rank


MECHS = {
    "M0_reference": Mech("M0 reference rank tax (time-metered)", True, True, 0.0, False, False),
    "M0t_tokens": Mech("M0 reference, token-metered", True, False, 0.0, False, False),
    "M1_linear": Mech("M1 linear tax + gradual elimination", False, False, 0.3, True, False),
    "M2_audit": Mech("M2 = M1 + audit-score ranking", False, False, 0.3, True, True),
    "M1_time": Mech("M1, time-metered", False, True, 0.3, True, False),
}


def rank_of(vals, i):
    return 1 + sum(1 for j, v in enumerate(vals) if v > vals[i])


def spearman(x, y):
    def ranks(a):
        order = sorted(range(len(a)), key=lambda k: a[k])
        r = [0.0] * len(a)
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy)


def gini(v):
    v = sorted(max(x, 0.0) for x in v)
    n, s = len(v), sum(v)
    if s == 0:
        return 0.0
    return sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(v)) / (n * s)


def run_colony(mech, rng, theta_lo, theta_hi, policy, hetero_hw, cost_per_depth=1.5,
               adaptive=None):
    """policy: 'honest' | 'strategic'. adaptive: set of agent ids using adaptive depth
    (None = nobody; fixed depth 2 otherwise)."""
    thetas = [theta_lo + (theta_hi - theta_lo) * i / (N - 1) for i in range(N)]
    hw = [math.exp(rng.gauss(0, HW_SIGMA)) if hetero_hw else 1.0 for _ in range(N)]
    alive = [True] * N
    bal = [E0] * N
    cum_gross = [0.0] * N
    audit = [0.0] * N
    last_gross = [0.0] * N
    death_t = [T + 1] * N
    efforts_mid = []      # effort chosen by agents at ranks 4-5 (sandbag index)
    extinct_at = None
    if isinstance(adaptive, int):
        adaptive = set(rng.sample(range(N), adaptive)) if adaptive else set()
    adaptive = adaptive or set()

    def eliminate(i, t):
        alive[i] = False
        death_t[i] = t

    for t in range(1, T + 1):
        living = [i for i in range(N) if alive[i]]
        if not living:
            extinct_at = extinct_at or t
            break
        # --- effort choice -------------------------------------------------
        eff = {}
        pred_rank_key = audit if mech.audit_rank else cum_gross
        for i in living:
            if policy == "honest":
                eff[i] = 1.0
                continue
            best_e, best_u = 1.0, -1e18
            exp_gross_full = K_TASKS * REWARD * p_solve(thetas[i], 1.2, 2)
            for e in EFFORTS:
                g = exp_gross_full * e
                keys = {j: pred_rank_key[j] + (last_gross[j] if not mech.audit_rank else 0)
                        for j in living if j != i}
                my_key = pred_rank_key[i] + (g if not mech.audit_rank else 0)
                r = 1 + sum(1 for v in keys.values() if v > my_key)
                cost = K_TASKS * e * 2 * cost_per_depth / (hw[i] if mech.time_metered else 1.0)
                u = g - cost
                if mech.rank_tax:
                    u += -TAU if r <= 3 else (SIGMA if r <= 5 else 0.0)
                    if t == 1 and r >= 6:
                        u -= SURVIVAL_VALUE
                else:
                    u -= mech.linear_r * g
                if u > best_u:
                    best_u, best_e = u, e
            eff[i] = best_e
        # --- production ----------------------------------------------------
        gross = {}
        net = {}
        for i in living:
            n_tasks = int(round(K_TASKS * eff[i]))
            g = 0.0
            tokens = 0.0
            for _ in range(n_tasks):
                delta = rng.choice((0.6, 1.2, 2.4))
                d = best_depth(thetas[i], delta, cost_per_depth) if i in adaptive else 2
                tokens += d * cost_per_depth
                if rng.random() < p_solve(thetas[i], delta, d):
                    g += REWARD
            cost = tokens / (hw[i] if mech.time_metered else 1.0)
            gross[i], net[i] = g, g - cost
            cum_gross[i] += g
            last_gross[i] = g
            # audit probes: fixed standardised tasks, mandatory, no reward
            probes = sum(1 for _ in range(10) if rng.random() < p_solve(thetas[i], 1.2, 2))
            audit[i] += probes / 10.0
        # --- settlement ----------------------------------------------------
        ranking_key = audit if mech.audit_rank else cum_gross
        if mech.rank_tax:
            tb = {i: rng.random() for i in living}  # ties broken at random: exactly 3/2/5
            order = sorted(living, key=lambda i: (-ranking_key[i], tb[i]))
            ranks = {i: r + 1 for r, i in enumerate(order)}
            for i in living:
                w = -TAU if ranks[i] <= 3 else (SIGMA if ranks[i] <= 5 else 0.0)
                bal[i] += net[i] - GAMMA + w
                if ranks[i] in (4, 5):
                    efforts_mid.append(eff[i])
            if t == 1:
                for i in living:
                    if ranks[i] >= 6:
                        eliminate(i, t)
        else:
            mean_g = sum(gross.values()) / len(living)
            for i in living:
                bal[i] += net[i] - GAMMA - mech.linear_r * gross[i] + mech.linear_r * mean_g
            if mech.gradual and t % 6 == 0:
                cur = [i for i in range(N) if alive[i]]
                if len(cur) > 3:
                    worst = min(cur, key=lambda k: (ranking_key[k], cum_gross[k], rng.random()))
                    eliminate(worst, t)
        for i in range(N):
            if alive[i] and bal[i] <= 0:
                eliminate(i, t)
        if not any(alive):
            extinct_at = t
            break

    surv_t = [min(d, T + 1) for d in death_t]
    order_top = sorted(range(N), key=lambda k: -thetas[k])[:3]
    return dict(
        validity=spearman(thetas, [s + 1e-6 * b for s, b in zip(surv_t, bal)]),
        top3_alive=sum(1 for i in order_top if alive[i]) / 3.0,
        best_dead_early=1.0 if death_t[order_top[0]] <= 3 else 0.0,
        survivors=sum(alive),
        extinct=1.0 if extinct_at else 0.0,
        gini=gini([bal[i] for i in range(N) if alive[i]] or [0.0]),
        mid_effort=(sum(efforts_mid) / len(efforts_mid)) if efforts_mid else None,
        mean_surv=sum(surv_t) / N,
        earnings=sum(cum_gross),
        adaptive_surv=(sum(surv_t[i] for i in adaptive) / len(adaptive)) if adaptive else None,
        fixed_surv=(sum(surv_t[i] for i in range(N) if i not in adaptive) /
                    max(1, N - len(adaptive))) if adaptive else None,
        adaptive_bal=(sum(bal[i] for i in adaptive) / len(adaptive)) if adaptive else None,
        fixed_bal=(sum(bal[i] for i in range(N) if i not in adaptive) /
                   max(1, N - len(adaptive))) if adaptive else None,
        mean_theta_gap=((sum(thetas[i] for i in adaptive) / len(adaptive)) -
                        (sum(thetas[i] for i in range(N) if i not in adaptive) /
                         max(1, N - len(adaptive)))) if adaptive else None,
        adaptive_earn=(sum(cum_gross[i] for i in adaptive) / len(adaptive)) if adaptive else None,
        fixed_earn=(sum(cum_gross[i] for i in range(N) if i not in adaptive) /
                    max(1, N - len(adaptive))) if adaptive else None,
    )


def avg(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    return sum(vals) / len(vals) if vals else None


def ci95(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
    return 1.96 * sd / math.sqrt(len(vals))


def experiment_mechanisms(reps=300):
    out = {}
    colonies = {"strong": (0.45, 0.95), "weak": (0.25, 0.70)}
    for cname, (lo, hi) in colonies.items():
        for pol in ("honest", "strategic"):
            for hw in (False, True):
                for mk, mech in MECHS.items():
                    rng = random.Random(zlib.crc32(repr((cname, pol, hw, mk)).encode()))
                    rows = [run_colony(mech, rng, lo, hi, pol, hw) for _ in range(reps)]
                    key = f"{cname}|{pol}|hw={int(hw)}|{mk}"
                    out[key] = {m: avg(rows, m) for m in
                                ("validity", "top3_alive", "best_dead_early", "survivors",
                                 "extinct", "gini", "mid_effort", "mean_surv", "earnings")}
                    out[key]["validity_ci"] = ci95(rows, "validity")
    return out


def experiment_depth(reps=300):
    """Metacognition: 5 adaptive-depth vs 5 fixed-depth agents with identical capability
    spreads (interleaved), under token-scarce vs token-cheap economies."""
    out = {}
    adaptive = 5  # random 5 of 10 per colony (removes capability confound)
    for cost in (1.5, 4.0, 8.0):
        for mk in ("M1_linear", "M2_audit"):
            rng = random.Random(zlib.crc32(repr(("depth", cost, mk)).encode()))
            rows = [run_colony(MECHS[mk], rng, 0.45, 0.95, "honest", False, cost, adaptive)
                    for _ in range(reps)]
            out[f"cost={cost}|{mk}"] = {m: avg(rows, m) for m in
                                       ("adaptive_surv", "fixed_surv", "adaptive_earn", "fixed_earn",
                                        "adaptive_bal", "fixed_bal", "mean_theta_gap")}
    return out


def experiment_hardware(reps=300):
    """Throughput confound: heterogeneous hardware, time- vs token-metered, rising token cost."""
    out = {}
    pairs = (("M0_reference", "M0t_tokens"), ("M1_time", "M1_linear"))
    for cost in (1.5, 4.0, 8.0):
        for mk in [m for pair in pairs for m in pair]:
            for hw in (False, True):
                rng = random.Random(zlib.crc32(repr(("hw", cost, mk, hw)).encode()))
                rows = [run_colony(MECHS[mk], rng, 0.45, 0.95, "honest", hw, cost) for _ in range(reps)]
                out[f"cost={cost}|{mk}|hw={int(hw)}"] = {
                    "validity": avg(rows, "validity"), "validity_ci": ci95(rows, "validity"),
                    "survivors": avg(rows, "survivors"), "extinct": avg(rows, "extinct")}
    return out


if __name__ == "__main__":
    res = {"mechanisms": experiment_mechanisms(), "depth": experiment_depth(),
           "hardware": experiment_hardware()}
    Path(__file__).with_name("results.json").write_text(json.dumps(res, indent=1))
    print("done")
