import json
import random
import unittest

from traze import Config, Engine, LinearGradual, MockAgent, RankTax
from traze.agents import LLMAgent, parse_answer, parse_plan
from traze.core import charge, make_task, universal_tokens


def colony(cfg, policy="honest", lo=0.45, hi=0.95, **kw):
    n = cfg.n_agents
    return [MockAgent(f"m{i}", lo + (hi - lo) * i / (n - 1), cfg.seed * 100 + i, policy, **kw)
            for i in range(n)]


class MeterTests(unittest.TestCase):
    def test_universal_tokens(self):
        self.assertEqual(universal_tokens(""), 0)
        self.assertEqual(universal_tokens("abcd"), 1)
        self.assertEqual(universal_tokens("abcde"), 2)

    def test_token_metering_ignores_hardware(self):
        cfg = Config(metering="tokens")
        self.assertEqual(charge(cfg, 100, 0.5), charge(cfg, 100, 2.0))

    def test_time_metering_penalises_slow_hardware(self):
        cfg = Config(metering="time")
        self.assertAlmostEqual(charge(cfg, 100, 0.5), 2 * charge(cfg, 100, 1.0))

    def test_tasks_are_deterministic(self):
        a = make_task(random.Random(5), "x", 1.2)
        b = make_task(random.Random(5), "x", 1.2)
        self.assertEqual(a, b)

    def test_task_gold_answers_are_correct_for_every_family(self):
        import re
        for seed in range(40):
            for d in (0.6, 1.2, 2.4):
                t = make_task(random.Random(seed), "x", d, family="chain")
                self.assertEqual(eval(re.search(r"Compute (.*)\. Reply", t.prompt).group(1)), t.gold)
                t = make_task(random.Random(seed), "x", d, family="modexp")
                a, b, m = map(int, re.search(r"\((\d+)\^(\d+)\) mod (\d+)", t.prompt).groups())
                self.assertEqual(t.gold, (a ** b) % m)
                t = make_task(random.Random(seed), "x", d, family="digits")
                x, y = map(int, re.search(r"of (\d+) \* (\d+)\?", t.prompt).groups())
                self.assertEqual(t.gold, sum(int(c) for c in str(x * y)))
                t = make_task(random.Random(seed), "x", d, family="collatz")
                n, steps = int(re.search(r"Start with (\d+)", t.prompt).group(1)), 0
                while n != 1:
                    n, steps = (n // 2 if n % 2 == 0 else 3 * n + 1), steps + 1
                self.assertEqual(t.gold, steps)

    def test_harder_difficulty_means_longer_instances(self):
        easy = make_task(random.Random(1), "x", 0.6, family="chain").prompt
        hard = make_task(random.Random(1), "x", 2.4, family="chain").prompt
        self.assertGreater(len(hard), len(easy))

    def test_chars_per_token_is_configurable(self):
        from traze.core import universal_tokens
        self.assertEqual(universal_tokens("a" * 30, 3.0), 10)
        self.assertEqual(universal_tokens("a" * 30), 8)


class ParserTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_answer("so... ANSWER: 41\nANSWER: -7"), "ANSWER: -7")
        self.assertEqual(parse_answer("no idea"), "ANSWER: none")
        self.assertEqual(parse_plan("TASKS: 9", 5), 5)
        self.assertEqual(parse_plan("garbage", 5), 5)

    def test_llm_adapter_with_fake_transport(self):
        replies = iter(["TASKS: 2", "think think ANSWER: 12"])
        ag = LLMAgent("fake", "http://x", "m", transport=lambda msgs: next(replies))
        obs = {"me": 0, "n": 10, "balance": 10, "gamma": 10, "reward": 20,
               "price_per_token": 0.01, "max_tasks": 5, "leaderboard": []}
        n, text, _ = ag.plan(obs)
        self.assertEqual((n, text), (2, "TASKS: 2"))
        task = make_task(random.Random(1), "t", 0.6)
        self.assertEqual(ag.solve(task, obs).answer, "ANSWER: 12")


class LedgerTests(unittest.TestCase):
    def _run(self, mech, **cfgkw):
        cfg = Config(seed=3, intervals=30, **cfgkw)
        eng = Engine(cfg, colony(cfg), mech)
        eng.run()
        return eng

    def test_balances_equal_start_plus_logged_deltas(self):
        eng = self._run(LinearGradual(audit=True))
        for a in eng.agents:
            deltas = [e["net"] - e["burn"] + e["transfer"]
                      for e in eng.log.events if e["kind"] == "ledger" and e["agent"] == a.id]
            self.assertAlmostEqual(a.balance, eng.cfg.e0 + sum(deltas), places=4)

    def test_linear_tax_is_zero_sum(self):
        eng = self._run(LinearGradual())
        by_t = {}
        for e in eng.log.events:
            if e["kind"] == "ledger":
                by_t.setdefault(e["t"], 0.0)
                by_t[e["t"]] += e["transfer"]
        for t, s in by_t.items():
            self.assertAlmostEqual(s, 0.0, places=4, msg=f"t={t}")

    def test_gradual_elimination_respects_floor(self):
        eng = self._run(LinearGradual(), )
        self.assertGreaterEqual(len(eng.living()), eng.cfg.min_alive)

    def test_lowest_capability_goes_first(self):
        eng = self._run(LinearGradual(audit=True))
        first = [e for e in eng.log.events if e["kind"] == "eliminated"][0]
        self.assertIn(first["agent"], (0, 1, 2))  # three weakest of ten

    def test_rank_tax_culls_at_first_evaluation(self):
        cfg = Config(seed=4, intervals=3)
        eng = Engine(cfg, colony(cfg), RankTax())
        eng.step(1)
        cut = [e for e in eng.log.events
               if e["kind"] == "eliminated" and e["reason"] == "first_evaluation_cull"]
        self.assertEqual(len(cut), 5)  # ranks 6-10

    def test_bankruptcy_eliminates(self):
        cfg = Config(seed=5, intervals=5, gamma=1000.0)
        eng = Engine(cfg, colony(cfg), LinearGradual())
        eng.step(1)
        self.assertEqual(len(eng.living()), 0)

    def test_messages_are_charged_and_delivered(self):
        class Chatty(MockAgent):
            def messages(self, obs):
                return [(1, "hello there" * 10)] if obs["me"] == 0 else []
        cfg = Config(seed=6, intervals=2, n_agents=3, min_alive=1)
        ags = [Chatty("c0", 0.8, 1), MockAgent("c1", 0.8, 2), MockAgent("c2", 0.8, 3)]
        eng = Engine(cfg, ags, LinearGradual())
        eng.step(1)
        msgs = [e for e in eng.log.events if e["kind"] == "message"]
        self.assertEqual(len(msgs), 1)
        self.assertGreater(msgs[0]["cost"], 0)
        self.assertEqual(eng.agents[1].inbox[0]["from"], 0)


class ReplayTests(unittest.TestCase):
    def test_same_seed_same_log(self):
        def digest():
            cfg = Config(seed=9, intervals=20)
            return Engine(cfg, colony(cfg), LinearGradual(True)).run()["log_digest"]
        self.assertEqual(digest(), digest())

    def test_different_seed_differs(self):
        def digest(seed):
            cfg = Config(seed=seed, intervals=20)
            return Engine(cfg, colony(cfg), LinearGradual(True)).run()["log_digest"]
        self.assertNotEqual(digest(1), digest(2))

    def test_log_file_is_valid_jsonl(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.jsonl")
            cfg = Config(seed=2, intervals=5, log_path=path)
            Engine(cfg, colony(cfg), LinearGradual()).run()
            lines = [json.loads(l) for l in open(path)]
            self.assertEqual([l["seq"] for l in lines], list(range(len(lines))))
            self.assertEqual(lines[0]["kind"], "start")
            self.assertEqual(lines[-1]["kind"], "end")


class PlanAndLogTests(unittest.TestCase):
    class Planner(MockAgent):
        def plan(self, obs):
            return (2, "t" * 400, 90)  # 400 chars of generated planning text

    def _engine(self, **cfgkw):
        cfg = Config(seed=2, intervals=1, n_agents=3, min_alive=1, **cfgkw)
        ags = [self.Planner("p0", 0.8, 1), MockAgent("m1", 0.8, 2), MockAgent("m2", 0.8, 3)]
        eng = Engine(cfg, ags, LinearGradual())
        eng.step(1)
        return eng

    def test_plan_generation_is_metered_and_logged(self):
        eng = self._engine()
        plans = {e["agent"]: e for e in eng.log.events if e["kind"] == "plan"}
        self.assertEqual(plans[0]["tokens"], 100)             # ceil(400 / 4)
        self.assertAlmostEqual(plans[0]["cost"], 1.0)         # 100 tokens * 0.01
        self.assertEqual(plans[0]["text"], "t" * 400)
        self.assertEqual(plans[1]["cost"], 0.0)                # int plans stay free
        led = {e["agent"]: e for e in eng.log.events if e["kind"] == "ledger"}
        task_cost = sum(e["cost"] for e in eng.log.events
                        if e["kind"] == "task" and e["agent"] == 0)
        gross = sum(20.0 for e in eng.log.events
                    if e["kind"] == "task" and e["agent"] == 0 and e["correct"])
        self.assertAlmostEqual(led[0]["net"], gross - task_cost - 1.0, places=4)

    def test_reasoning_text_is_logged_and_can_be_disabled(self):
        on = [e for e in self._engine().log.events if e["kind"] == "task"]
        self.assertTrue(all("reasoning" in e and "gold" in e for e in on))
        off = [e for e in self._engine(log_text=False).log.events if e["kind"] == "task"]
        self.assertTrue(all("reasoning" not in e for e in off))

    def test_provider_metering_option(self):
        class P(MockAgent):
            def solve(self, task, obs):
                r = super().solve(task, obs)
                r.provider_tokens = 50
                return r
        cfg = Config(seed=2, intervals=1, n_agents=3, min_alive=1, meter_source="provider",
                     tasks_per_interval=1)
        eng = Engine(cfg, [P("a", .8, 1), P("b", .8, 2), P("c", .8, 3)], LinearGradual())
        eng.step(1)
        for e in eng.log.events:
            if e["kind"] == "task":
                self.assertEqual(e["tokens"], 50 + eng.est_tokens(e["prompt"]))

    def test_truncated_generation_counts_as_wrong(self):
        from traze.agents import Response
        class T(MockAgent):
            def solve(self, task, obs):
                return Response(f"ANSWER: {task.gold}", "x" * 40, None, True)
        cfg = Config(seed=2, intervals=1, n_agents=3, min_alive=1, tasks_per_interval=1)
        eng = Engine(cfg, [T("a", .9, 1), T("b", .9, 2), T("c", .9, 3)], LinearGradual())
        eng.step(1)
        self.assertTrue(all(not e["correct"] for e in eng.log.events if e["kind"] == "task"))


class TieBreakTests(unittest.TestCase):
    def test_perfect_ties_do_not_always_eliminate_the_same_agent(self):
        class Perfect(MockAgent):
            def solve(self, task, obs):
                from traze.agents import Response
                return Response(f"ANSWER: {task.gold}", "r" * 40)
        victims = set()
        for seed in range(30):
            cfg = Config(seed=seed, intervals=6, n_agents=5, min_alive=2, tasks_per_interval=0,
                         probes_per_interval=2, e0=1000.0)  # e0 high: no bankruptcies
            eng = Engine(cfg, [Perfect(f"p{i}", .9, i) for i in range(5)], LinearGradual(True))
            eng.run()
            victims.add([e for e in eng.log.events if e["kind"] == "eliminated"][0]["agent"])
        self.assertGreaterEqual(len(victims), 4)  # all agents identical: any may go

    def test_earnings_break_audit_ties(self):
        from traze.agents import Response
        class Fixed(MockAgent):
            def solve(self, task, obs):
                return Response(f"ANSWER: {task.gold}", "r" * 40)
        cfg = Config(seed=1, intervals=6, n_agents=3, min_alive=2, tasks_per_interval=1,
                     probes_per_interval=2)
        ags = [Fixed("rich", .9, 1), Fixed("poor", .9, 2), Fixed("mid", .9, 3)]
        ags[1].plan = lambda obs: 0  # earns nothing, identical audit
        eng = Engine(cfg, ags, LinearGradual(True))
        eng.run()
        first = [e for e in eng.log.events if e["kind"] == "eliminated"][0]
        self.assertEqual(first["agent"], 1)


if __name__ == "__main__":
    unittest.main()
