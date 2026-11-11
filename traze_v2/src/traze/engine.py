"""Orchestrator: serves tasks, meters tokens, grades, runs messages, settles, logs."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .agents import Agent
from .core import (DIFFICULTIES, PROBE_DIFFICULTY, Config, Task, charge, make_task, new_log,
                   universal_tokens)
from .mechanisms import Mechanism


@dataclass
class AgentState:
    id: int
    agent: Agent
    alive: bool = True
    balance: float = 0.0
    cum_gross: float = 0.0
    audit: float = 0.0
    death_t: int | None = None
    inbox: list = field(default_factory=list)


class Engine:
    def __init__(self, cfg: Config, agents: list[Agent], mechanism: Mechanism):
        assert len(agents) == cfg.n_agents
        self.cfg, self.mech = cfg, mechanism
        self.agents = [AgentState(i, a, balance=cfg.e0) for i, a in enumerate(agents)]
        self.task_rng = random.Random(cfg.seed)
        self.tie_rng = random.Random(cfg.seed + 1)  # fresh, seeded tie-break draws per evaluation
        self.log = new_log(cfg)
        self.log.write("start", 0, mechanism=mechanism.name, config={
            k: v for k, v in vars(cfg).items() if k != "log_path"},
            agents=[a.name for a in agents])

    # -- state helpers ------------------------------------------------------------------
    def draw_ties(self, ids) -> dict:
        """Fresh random tie-break values, drawn in id order so a seeded run replays exactly.
        A new draw per evaluation means no agent is permanently favoured in ties."""
        return {i: self.tie_rng.random() for i in sorted(ids)}

    def est_tokens(self, text: str) -> int:
        return universal_tokens(text, self.cfg.chars_per_token)

    def living(self):
        return [a for a in self.agents if a.alive]

    def eliminate(self, i: int, t: int, reason: str):
        a = self.agents[i]
        if a.alive:
            a.alive, a.death_t = False, t
            self.log.write("eliminated", t, agent=i, reason=reason, balance=round(a.balance, 6))

    def _obs(self, st: AgentState, t: int) -> dict:
        key = self.mech.rank_key(self)
        board = sorted(key.items(), key=lambda kv: (-kv[1], -self.agents[kv[0]].cum_gross, kv[0]))
        inbox, st.inbox = st.inbox, []
        return {"t": t, "me": st.id, "n": self.cfg.n_agents, "balance": st.balance,
                "gamma": self.cfg.gamma, "reward": self.cfg.reward,
                "price_per_token": self.cfg.price_per_token,
                "max_tasks": self.cfg.tasks_per_interval,
                "leaderboard": [(i, round(v, 4)) for i, v in board],
                "schedule": self.mech.schedule(self.cfg), "inbox": inbox}

    # -- one interval -------------------------------------------------------------------
    def step(self, t: int) -> bool:
        cfg = self.cfg
        living = self.living()
        if not living:
            return False
        gross, net = {}, {}
        obs = {st.id: self._obs(st, t) for st in living}

        for st in living:
            plan = st.agent.plan(obs[st.id])
            text, ptoks = "", None
            if isinstance(plan, tuple):
                plan, text, ptoks = plan
            n = max(0, min(cfg.tasks_per_interval, int(plan)))
            plan_tokens = self._meter(text, ptoks, 0)
            plan_cost = charge(cfg, plan_tokens, st.agent.throughput) if text else 0.0
            self.log.write("plan", t, agent=st.id, tasks=n, tokens=plan_tokens,
                           cost=round(plan_cost, 6), provider_tokens=ptoks,
                           **({"text": text} if cfg.log_text else {}))
            g, cost = 0.0, plan_cost
            for k in range(n):
                task = make_task(self.task_rng, f"t{t}-a{st.id}-{k}",
                                 self.task_rng.choice(DIFFICULTIES))
                ok, c = self._run_task(st, task, obs[st.id], t)
                g += cfg.reward if ok else 0.0
                cost += c
            msg_cost = self._send_messages(st, obs[st.id], t)
            gross[st.id], net[st.id] = g, g - cost - msg_cost
            st.cum_gross += g

        for st in living:  # audit probes: standardised, unpaid, never charged
            solved = 0
            for k in range(cfg.probes_per_interval):
                task = make_task(self.task_rng, f"p{t}-a{st.id}-{k}", PROBE_DIFFICULTY, True)
                resp = st.agent.solve(task, obs[st.id])
                solved += (not resp.truncated) and resp.answer.strip() == f"ANSWER: {task.gold}"
            st.audit += solved / cfg.probes_per_interval
            self.log.write("probe", t, agent=st.id, solved=solved)

        self.mech.settle(self, t, gross, net)
        board = sorted(self.mech.rank_key(self).items(), key=lambda kv: -kv[1])
        self.log.write("leaderboard", t, board=[(i, round(v, 4)) for i, v in board])
        return bool(self.living())

    def _run_task(self, st: AgentState, task: Task, obs: dict, t: int):
        resp = st.agent.solve(task, obs)
        tokens = self._meter(resp.reasoning + resp.answer, resp.provider_tokens,
                             self.est_tokens(task.prompt))
        cost = charge(self.cfg, tokens, st.agent.throughput)
        ok = (not resp.truncated) and resp.answer.strip() == f"ANSWER: {task.gold}"
        self.log.write("task", t, agent=st.id, task=task.task_id, difficulty=task.difficulty,
                       tokens=tokens, est_tokens=self.est_tokens(resp.reasoning + resp.answer),
                       cost=round(cost, 6), correct=ok, answer=resp.answer,
                       truncated=resp.truncated, reasoning_chars=len(resp.reasoning),
                       provider_tokens=resp.provider_tokens,
                       **({"prompt": task.prompt, "gold": task.gold, "reasoning": resp.reasoning}
                          if self.cfg.log_text else {}))
        return ok, cost

    def _meter(self, text: str, provider_tokens, prompt_tokens: int) -> int:
        """Tokens to charge for one generation. Default: the universal character rule, so models
        with different tokenisers pay the same for the same text."""
        if self.cfg.meter_source == "provider" and provider_tokens:
            return prompt_tokens + int(provider_tokens)
        return prompt_tokens + self.est_tokens(text)

    def _send_messages(self, st: AgentState, obs: dict, t: int) -> float:
        total = 0.0
        for to, text in st.agent.messages(obs):
            if not (0 <= to < len(self.agents)) or not self.agents[to].alive:
                continue
            tokens = universal_tokens(text)
            c = tokens * self.cfg.message_price_per_token
            total += c
            self.agents[to].inbox.append({"from": st.id, "text": text})
            self.log.write("message", t, frm=st.id, to=to, tokens=tokens, cost=round(c, 6),
                           text=text)
        return total

    # -- whole run ----------------------------------------------------------------------
    def run(self) -> dict:
        for t in range(1, self.cfg.intervals + 1):
            if not self.step(t):
                break
        summary = {
            "mechanism": self.mech.name,
            "survivors": [a.id for a in self.agents if a.alive],
            "death_t": {a.id: a.death_t for a in self.agents},
            "balances": {a.id: round(a.balance, 2) for a in self.agents},
            "audit": {a.id: round(a.audit, 2) for a in self.agents},
        }
        self.log.write("end", self.cfg.intervals, **summary)
        summary["log_digest"] = self.log.digest()
        return summary
