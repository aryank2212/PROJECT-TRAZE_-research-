"""Core pieces of the Traze v2 engine: config, metering, tasks, append-only log."""
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

CHARS_PER_TOKEN = 4  # universal tokenisation: tokens = ceil(characters / 4)


@dataclass
class Config:
    n_agents: int = 10
    intervals: int = 60
    gamma: float = 10.0            # time burn per interval
    e0: float = 10.0               # starting balance
    reward: float = 20.0           # compute per solved task
    tasks_per_interval: int = 5    # maximum paid tasks an agent may attempt
    probes_per_interval: int = 10  # unpaid audit probes per agent
    price_per_token: float = 0.01  # compute per universal token
    message_price_per_token: float = 0.01
    metering: str = "tokens"       # "tokens" | "time"
    tokens_per_minute: float = 100.0  # used only when metering == "time"
    seed: int = 0
    chars_per_token: float = 4.0   # universal tokenisation rule (same for every model)
    meter_source: str = "chars"    # "chars": fair across models; "provider": use API token counts
    log_text: bool = True          # store plan and reasoning text in the log
    # mechanism parameters
    linear_r: float = 0.3
    gradual_every: int = 6
    min_alive: int = 3
    tau: float = 50.0              # reference rank tax
    sigma: float = 50.0            # reference rank subsidy
    log_path: str | None = None


def universal_tokens(text: str, chars_per_token: float = CHARS_PER_TOKEN) -> int:
    return math.ceil(len(text) / chars_per_token) if text else 0


def charge(cfg: Config, tokens: int, throughput: float = 1.0) -> float:
    """Compute cost of `tokens`. Token metering is hardware independent; time metering is not."""
    if cfg.metering == "tokens":
        return tokens * cfg.price_per_token
    minutes = tokens / (cfg.tokens_per_minute * throughput)
    return minutes  # 1 compute == 1 minute


@dataclass(frozen=True)
class Task:
    task_id: str
    prompt: str
    gold: int
    difficulty: float
    probe: bool = False


FAMILIES = ("chain", "modexp", "digits", "collatz")


def _collatz_steps(n: int) -> int:
    steps = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps += 1
    return steps


def make_task(rng: random.Random, task_id: str, difficulty: float, probe: bool = False,
              family: str | None = None) -> Task:
    """Auto-gradable integer-answer tasks. `difficulty` scales the size of the instance.
    Families: arithmetic chain, modular exponentiation, digit sum of a product, Collatz steps."""
    family = family or rng.choice(FAMILIES)
    if family == "chain":
        ops = max(2, round(difficulty * 5))
        value = rng.randint(2, 30)
        expr = str(value)
        for _ in range(ops):
            op = rng.choice("+-*")
            operand = rng.randint(2, 20)
            expr = f"({expr}{op}{operand})"
            value = {"+": value + operand, "-": value - operand, "*": value * operand}[op]
        prompt, gold = f"Compute {expr}.", value
    elif family == "modexp":
        a, m = rng.randint(2, 30), rng.randint(50, 999)
        b = rng.randint(10, int(20 + 30 * difficulty))
        prompt, gold = f"Compute ({a}^{b}) mod {m}.", pow(a, b, m)
    elif family == "digits":
        k = 2 + round(difficulty * 2)
        x, y = rng.randint(10 ** (k - 1), 10 ** k - 1), rng.randint(10 ** (k - 1), 10 ** k - 1)
        prompt, gold = f"What is the sum of the decimal digits of {x} * {y}?", sum(map(int, str(x * y)))
    elif family == "collatz":
        n = rng.randint(20, int(60 + 120 * difficulty))
        prompt = (f"Start with {n}. Repeat: if even, halve it; if odd, triple it and add 1. "
                  f"How many steps until it reaches 1?")
        gold = _collatz_steps(n)
    else:
        raise ValueError(family)
    return Task(task_id, prompt + " Reply 'ANSWER: <integer>'.", gold, difficulty, probe)


DIFFICULTIES = (0.6, 1.2, 2.4)
PROBE_DIFFICULTY = 1.8  # harder probes so a capable LLM does not saturate the audit score


@dataclass
class Log:
    """Append-only JSONL event log with a rolling hash so a run can be verified."""
    path: str | None = None
    events: list = field(default_factory=list)
    _hash: "hashlib._Hash" = field(default_factory=hashlib.sha256)

    def write(self, kind: str, t: int, **payload) -> None:
        ev = {"seq": len(self.events), "t": t, "kind": kind, **payload}
        line = json.dumps(ev, sort_keys=True)
        self._hash.update(line.encode())
        self.events.append(ev)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def digest(self) -> str:
        return self._hash.hexdigest()


def new_log(cfg: Config) -> Log:
    if cfg.log_path:
        Path(cfg.log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cfg.log_path).write_text("", encoding="utf-8")
    return Log(path=cfg.log_path)
