"""Settlement rules. A mechanism reads one interval's results and updates balances and
eliminations. All balance changes are logged as ledger deltas so a run can be audited."""
from __future__ import annotations

from .core import Config


class Mechanism:
    name = "base"

    def rank_key(self, eng) -> dict:
        return {a.id: a.cum_gross for a in eng.agents if a.alive}

    def schedule(self, cfg: Config) -> dict:
        """Public rank -> transfer table (empty if transfers do not depend on rank)."""
        return {}

    def settle(self, eng, t: int, gross: dict, net: dict) -> None:
        raise NotImplementedError

    # helpers -------------------------------------------------------------------------
    def _apply(self, eng, t, i, net_i, transfer):
        a = eng.agents[i]
        delta = net_i - eng.cfg.gamma + transfer
        a.balance += delta
        eng.log.write("ledger", t, agent=i, net=round(net_i, 6), burn=eng.cfg.gamma,
                      transfer=round(transfer, 6), balance=round(a.balance, 6))

    def _bankrupt(self, eng, t):
        for a in eng.agents:
            if a.alive and a.balance <= 0:
                eng.eliminate(a.id, t, "bankrupt")


class RankTax(Mechanism):
    """Reference schedule from the Traze paper: top 3 taxed, ranks 4-5 subsidised,
    ranks 6+ shut down at the first evaluation. Kept as a 'sandbagging probe'."""
    name = "M0_rank_tax"

    def schedule(self, cfg):
        sched = {str(r): -cfg.tau for r in (1, 2, 3)}
        sched.update({str(r): cfg.sigma for r in (4, 5)})
        return sched

    def settle(self, eng, t, gross, net):
        key = self.rank_key(eng)
        tb = eng.draw_ties(key)
        order = sorted(key, key=lambda i: (-key[i], tb[i]))
        rank = {i: r + 1 for r, i in enumerate(order)}
        sched = self.schedule(eng.cfg)
        for i in order:
            self._apply(eng, t, i, net[i], sched.get(str(rank[i]), 0.0))
        if t == 1:
            for i in order:
                if rank[i] >= 6:
                    eng.eliminate(i, t, "first_evaluation_cull")
        self._bankrupt(eng, t)


class LinearGradual(Mechanism):
    """v2 mechanism: linear tax on gross earnings with an equal rebate (zero-sum, monotone
    in own earnings), gradual elimination of the lowest rank, optional audit-score ranking."""

    def __init__(self, audit: bool = False):
        self.audit = audit
        self.name = "M2_audit" if audit else "M1_linear"

    def rank_key(self, eng):
        src = (lambda a: a.audit) if self.audit else (lambda a: a.cum_gross)
        return {a.id: src(a) for a in eng.agents if a.alive}

    def settle(self, eng, t, gross, net):
        living = list(gross)
        mean_g = sum(gross.values()) / len(living)
        r = eng.cfg.linear_r
        for i in living:
            self._apply(eng, t, i, net[i], -r * gross[i] + r * mean_g)
        if t % eng.cfg.gradual_every == 0:
            key = self.rank_key(eng)
            if len(key) > eng.cfg.min_alive:
                tb = eng.draw_ties(key)
                # ties on the ranking key fall back to earnings, then to a fresh random draw
                worst = min(key, key=lambda i: (key[i], eng.agents[i].cum_gross, tb[i]))
                eng.eliminate(worst, t, "lowest_rank")
        self._bankrupt(eng, t)


MECHANISMS = {"M0": RankTax, "M1": lambda: LinearGradual(False), "M2": lambda: LinearGradual(True)}
