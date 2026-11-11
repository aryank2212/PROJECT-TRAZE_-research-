"""Cross-check the engine against sim.py: many mock colonies per mechanism.

  PYTHONPATH=src python3 src/batch.py
"""
import math
import random

from traze import Config, Engine, MockAgent
from traze.mechanisms import MECHANISMS


def spearman(x, y):
    def ranks(a):
        order = sorted(range(len(a)), key=lambda k: a[k]); r = [0.0] * len(a); i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y); mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx)); sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return 0.0 if sx == 0 or sy == 0 else sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy)


def colony(cfg, policy, lo, hi, hw_sigma=0.0, rng=None):
    n = cfg.n_agents
    return [MockAgent(f"m{i}", lo + (hi - lo) * i / (n - 1), cfg.seed * 100 + i, policy,
                      throughput=math.exp(rng.gauss(0, hw_sigma)) if hw_sigma else 1.0)
            for i in range(n)]


def run(mech, policy, lo, hi, seeds, metering="tokens", hw_sigma=0.0, price=0.01, tpm=100.0):
    val, surv, ext = [], [], []
    for s in range(seeds):
        cfg = Config(seed=s, metering=metering, price_per_token=price, tokens_per_minute=tpm)
        ags = colony(cfg, policy, lo, hi, hw_sigma, random.Random(s))
        eng = Engine(cfg, ags, MECHANISMS[mech]()); eng.run()
        thetas = [a.agent.theta for a in eng.agents]
        T = cfg.intervals
        life = [(a.death_t or T + 1) + 1e-6 * a.balance for a in eng.agents]
        val.append(spearman(thetas, life)); surv.append(len(eng.living()))
        ext.append(0.0 if eng.living() else 1.0)
    m = lambda v: sum(v) / len(v)
    return m(val), m(surv), m(ext)


if __name__ == "__main__":
    S = 100
    print(f"{'config':44s} validity survivors extinct   (sim.py reference)")
    rows = [
        ("strong honest   M0 rank tax", "M0", "honest", .45, .95, "0.43 / 4.8 / 0.00"),
        ("strong strategic M0 rank tax", "M0", "strategic", .45, .95, "0.57 / 3.3 / 0.00"),
        ("strong honest   M1 linear", "M1", "honest", .45, .95, "0.96 / 3.0 / 0.00"),
        ("strong honest   M2 audit", "M2", "honest", .45, .95, "0.98 / 3.0 / 0.00"),
        ("strong strategic M2 audit", "M2", "strategic", .45, .95, "0.98 / 3.0 / 0.00"),
        ("weak   honest   M0 rank tax", "M0", "honest", .25, .70, "0.36 / 0.1 / 0.91"),
        ("weak   honest   M2 audit", "M2", "honest", .25, .70, "0.96 / 3.0 / 0.00"),
    ]
    for label, mech, pol, lo, hi, ref in rows:
        v, s, e = run(mech, pol, lo, hi, S)
        print(f"{label:44s} {v:7.2f} {s:9.2f} {e:7.2f}   {ref}")
    print("\nHardware confound (strong, honest, mixed hardware, M1); 1 compute/min at 1/price tokens/min:")
    for price in (0.01, 0.027, 0.053):
        for metering in ("tokens", "time"):
            v, s_, e = run("M1", "honest", .45, .95, S, metering=metering, hw_sigma=0.4,
                           price=price, tpm=1.0 / price)
            print(f"  price={price:<6} {metering:7s} validity={v:.2f} survivors={s_:.2f} extinct={e:.2f}")
