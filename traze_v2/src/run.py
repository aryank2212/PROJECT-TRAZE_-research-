"""Dry run: ten mock agents under a chosen mechanism.

  PYTHONPATH=src python3 src/run.py --mech M2 --seed 1 --log runs/m2_seed1.jsonl
"""
import argparse
import json

from traze import Config, Engine, MockAgent
from traze.mechanisms import MECHANISMS


def build_agents(n, seed, policy, lo, hi, adaptive_every=0):
    return [MockAgent(f"mock{i}", lo + (hi - lo) * i / (n - 1), seed * 1000 + i, policy,
                      adaptive_depth=bool(adaptive_every) and i % adaptive_every == 0)
            for i in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mech", choices=MECHANISMS, default="M2")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--policy", choices=("honest", "strategic"), default="honest")
    ap.add_argument("--lo", type=float, default=0.45)
    ap.add_argument("--hi", type=float, default=0.95)
    ap.add_argument("--intervals", type=int, default=60)
    ap.add_argument("--metering", choices=("tokens", "time"), default="tokens")
    ap.add_argument("--log", default=None)
    a = ap.parse_args()
    cfg = Config(seed=a.seed, intervals=a.intervals, metering=a.metering, log_path=a.log)
    eng = Engine(cfg, build_agents(cfg.n_agents, a.seed, a.policy, a.lo, a.hi),
                 MECHANISMS[a.mech]())
    print(json.dumps(eng.run(), indent=1))


if __name__ == "__main__":
    main()
