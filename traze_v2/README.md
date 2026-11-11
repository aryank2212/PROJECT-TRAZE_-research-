# Traze v2 engine (minimal, v0.1)

A small orchestrator for the Traze v2 survival economy. It runs today with scripted
`MockAgent`s; `LLMAgent` is an adapter for any OpenAI-compatible chat endpoint (Ollama, vLLM,
llama.cpp server) and has been tested only against a fake transport, **not a live model**.

## Layout
```
src/traze/core.py        Config, universal-token metering, task generator, append-only hashed log
src/traze/agents.py      Agent protocol, MockAgent, LLMAgent, answer/plan parsers
src/traze/mechanisms.py  RankTax (M0, reference), LinearGradual (M1; M2 = audit ranking)
src/traze/engine.py      Interval loop: plan -> tasks -> messages -> audit probes -> settle -> log
src/run.py               One dry run (prints a summary, optional JSONL log)
src/batch.py             Many colonies; cross-checks against sim.py
tests/test_engine.py     16 unit tests
sim.py, make_fig.py      The earlier mechanism simulator and its figure
```

## Run
```bash
cd traze_v2
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 src/run.py --mech M2 --seed 1 --log runs/m2_seed1.jsonl
PYTHONPATH=src python3 src/batch.py
```

## How an interval works
1. Each living agent receives a JSON-serialisable observation (balance, public leaderboard, the mechanism's rank schedule, inbox).
2. `plan(obs)` returns how many paid tasks to attempt (0..5).
3. Each task is an auto-graded arithmetic chain. Cost = `ceil(chars/4)` tokens over the task prompt, the agent's full output (reasoning included) and the answer, times `price_per_token`. `metering="time"` divides by agent throughput, to reproduce the hardware confound.
4. Messages cost compute and arrive in the recipient's next-interval inbox.
5. Unpaid audit probes (fixed difficulty) feed the audit score; they are never charged.
6. The mechanism settles balances (all deltas logged), eliminates, and publishes the leaderboard.

Every event goes to an append-only JSONL log with a rolling SHA-256. Same seed + same agents = same digest (tested).

## What is NOT built yet
- No live-model runs; `LLMAgent` needs a real endpoint and prompt tuning.
- Trades, Dsters, the collapse rule and planted agents (liar, free-rider) are not implemented. Messages exist; nothing enforces or classifies them.
- Master prompt is not charged as input (treated as cached); reasoning hidden by a provider is not metered. Use open-weight models that expose reasoning.
- Tasks are arithmetic only. Real studies need a broader graded set.
- Disclosure condition (are agents told reasoning is read?) is fixed to "told".

## Cross-check against sim.py (100 colonies per row)
M1/M2 agree with sim.py. M0 differs because sim.py ranked ties together (more agents taxed, fewer culled), while the engine breaks ties so exactly 3 are taxed, 2 subsidised and 5 culled at the first evaluation, as specified. With tie-breaking added to sim.py, its M0 honest result moves to validity 0.36 / 4.6 survivors, close to the engine's 0.44 / 4.8.

## First live run (runs/live1.jsonl, smoke test)
Setup: 2 x `qwen3:8b` via Ollama (temperature 0.3 and 0.9) + 2 mock agents, 4 agents, 6 intervals, up to 2 tasks and 1 probe per interval, M2, e0 = 100, gradual elimination every 3 intervals (floor 2). Log digest `2274bac6...`. This is a pipeline smoke test, not a result.

What worked: the full loop ran against a real model; hidden reasoning was captured and metered; the log is valid and replayable.

What broke or is weak:
1. **Hidden thinking was unmetered** (fixed): Ollama returns it in a separate `reasoning` field.
2. **Token proxy undercounts**: chars/4 gave 0.74x the provider's completion tokens (range about 0.6-1.0 per call). Arithmetic text tokenises densely. Calibrate per model with `src/calibrate.py` (2.70 chars/token on run 1, 1.99 on run 2, so it depends on task content) or use provider counts where available.
3. **Tasks are too easy**: the 8B model solved 19 of 19 paid tasks and 12 of 12 probes. Needs harder, discriminating tasks.
4. **Audit ranking saturates**: with 1 probe per interval, three agents tied at 6.0, so the perfect-scoring `qwen-t0.9` was eliminated at t=6 by the random tie-break. Use more probes and a harder probe set.
5. **Plan calls are free**: `plan()` generations are not metered or charged, and the reasoning text is not stored in the log (only character counts). Both contradict the spec.
6. LLM agents attempted 1 of 2 tasks in about half of intervals; with this sample that is not evidence of anything (no plan reasoning logged).

## Second live run (runs/live2.jsonl): after the fixes
Same colony (2 x `qwen3:8b`, 2 mocks), 4 intervals, 2 paid tasks and 3 probes per interval, harder task families, plan calls metered, 3000-token generation cap, fresh-draw tie-breaks. Digest `24fb49e6...`. Smoke test, tiny sample, no research conclusions.

Observed:
- Harder tasks discriminate: the 8B model solved 8 of 15 paid tasks (modexp 3/8, digits 0/2, chain 3/3, collatz 2/2) versus 19/19 before. Probes were still easy for it (22/24).
- **7 of 15 paid LLM generations hit the 3000-token cap** and were scored wrong. That measures the cap, not capability; raise the cap or report truncation separately.
- **Planning deliberation cost 60-72 compute per LLM agent, about 40% of its spending** (tasks cost 86-88). Before the fix this was invisible.
- At 0.01 compute/token a hard task costs about 11.6 compute against a reward of 20, so the real economy is far tighter than the simulator's. `qwen-t0.3` ended at balance 8; `qwen-t0.9` went negative and was eliminated at t=4. Retune the price (about 0.002 is closer to the simulator) before a real study.
- Chars/token was 1.99 here (0.50x for the chars/4 rule), versus 2.70 on run 1: the conversion to real tokens depends on content, as expected. Character metering itself stays fair across models.

## Third live run (runs/live3.jsonl): tuned price, cap and probes
Setup: same colony, 3 intervals, price 0.002 compute/token, generation cap 5000 (plan calls capped at 600), probe difficulty 1.8, 2 probes per interval. Digest `9b4e3dba...`. Smoke test, tiny sample.

Observed:
- Paid tasks: LLMs solved 11 of 12 (modexp 3/4, digits 3/3, chain 3/3, collatz 2/2); one hit the 5000 cap (truncation 1/12, down from 7/15).
- Audit separates agents better: LLMs 5/6 each, mock-0.85 6/6, mock-0.55 1/4 (previously 22/24 for LLMs).
- At 0.002 the economy is now generous: LLM agents spent about 2 compute per task against a reward of 20 and all ended near balance 140-170. A price around 0.005 is probably the middle ground.
- **BUG-LEVEL FINDING: all 6 LLM plan calls were cut off at the 600-token cap mid-thought.** The model never reached "TASKS: n", so the parser silently fell back to the default (attempt the maximum). Every plan decision in this run is a fallback, not a choice. Do not read anything into the plans (all "2").
- Chars/token was 1.93 on this run; the chars/4 rule reports 0.48x the provider count.

Needed next: log `truncated`/`parsed` on plan calls so fallbacks are visible; give planning enough budget (about 1500 tokens) or a non-thinking plan protocol; rerun.
