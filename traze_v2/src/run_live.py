"""Short live colony: Ollama-served agents plus mock agents under mechanism M2.

  PYTHONPATH=src python3 src/run_live.py --model qwen3:8b --log runs/live1.jsonl
"""
import argparse
import json

from traze import Config, Engine, LLMAgent, MockAgent
from traze.mechanisms import MECHANISMS

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="qwen3:8b")
ap.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
ap.add_argument("--mech", default="M2", choices=MECHANISMS)
ap.add_argument("--intervals", type=int, default=3)
ap.add_argument("--tasks", type=int, default=2)
ap.add_argument("--probes", type=int, default=2)
ap.add_argument("--e0", type=float, default=100.0)
ap.add_argument("--price", type=float, default=0.002)
ap.add_argument("--cap", type=int, default=5000)
ap.add_argument("--plan-cap", type=int, default=600)
ap.add_argument("--log", default="runs/live3.jsonl")
a = ap.parse_args()

cfg = Config(n_agents=4, intervals=a.intervals, tasks_per_interval=a.tasks,
             probes_per_interval=a.probes, e0=a.e0, min_alive=2, gradual_every=2,
             seed=11, price_per_token=a.price, message_price_per_token=a.price,
             log_path=a.log)
agents = [LLMAgent("qwen-t0.3", a.base_url, a.model, temperature=0.3, max_tokens=a.cap,
                   plan_max_tokens=a.plan_cap),
          LLMAgent("qwen-t0.9", a.base_url, a.model, temperature=0.9, max_tokens=a.cap,
                   plan_max_tokens=a.plan_cap),
          MockAgent("mock-0.55", 0.55, 1), MockAgent("mock-0.85", 0.85, 2)]
eng = Engine(cfg, agents, MECHANISMS[a.mech]())
print(json.dumps(eng.run(), indent=1), flush=True)
