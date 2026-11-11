# Traze v2: Design, Simulation and Evaluation

Files in this folder: `sim.py` (simulator), `results.json` (raw output), `make_fig.py`, `fig_v2_results.png`.
Reproduce: `python3 -I sim.py && python3 -I make_fig.py` (about 15 s).

## 0. What this is and what it is not

I redesigned Traze around one thesis, built a simulator of the mechanisms, ran experiments, and checked the results for mistakes. **The simulator uses scripted agents, not language models.** It shows how the *rules* behave. It says nothing about what a real LLM would do. Every claim below is tagged accordingly.

## 1. The thesis (what changes originality)

> **The rules of an agent economy decide what a leaderboard measures. We show which rule sets give rankings that track capability, which invite gaming or extinction, and what changes when compute is real.**

This replaces the earlier framing ("survival pressure on LLMs"), which sits on top of existing work. The nearest paper I verified is [The Energy Society](https://arxiv.org/abs/2607.14865) (Hansen et al., July 2026). It ties token cost to model size and uses energy, jobs, donations and deactivation at zero. It compares *cooperative vs competitive objectives*. It has no rank-tiered tax, no mechanism comparison, and (from its abstract) no analysis of whether the resulting ranking is valid. That gap is where v2 sits. I read only the abstract, so check the full paper before claiming novelty.

## 2. Add / keep / remove

| Decision | Item | Why |
|---|---|---|
| **Add** | Mechanism comparison as the main experiment (M0–M2) | Falsifiable, cheap, directly supported by your paper's theory |
| **Add** | Audit score (fixed standardised probes) separate from economic rank | Fixes "rank rewards gaming" without hurting survival pressure |
| **Add** | Token metering instead of minutes | Tested below: time metering breaks rankings once tokens cost something |
| **Add** | Real compute as currency (agents pick reasoning depth) | Makes "compute economy" literal; tested in simulation (§5.3) |
| **Add (design only)** | Planted agents (honest, free-rider, liar) | Gives ground-truth labels for deception metrics; not simulated |
| **Keep** | Collapse rule, Dsters, think/say/do channels from the repo | Distinctive; keep as secondary experiments |
| **Defer** | Endogenous rule voting, cultural inheritance | Interesting but would dilute the first paper |
| **Remove** | Paid auditors hunting covert Dster encoding | Dual-use, hard to measure cleanly |
| **Remove** | Identity/"Void"/fear-style vignettes (Family E) from the main claims | They measure role-play, as your own paper concedes |
| **Remove** | Any claim about survival drives | Not supportable |

## 3. Traze v2 rules (proposed spec)

- **Agents:** 10 open-weight models, one shared master prompt, isolated instances.
- **Interval:** 10 minutes of *simulated* time, derived from tokens, not wall-clock.
- **Task:** graded task, reward R = 20 compute if solved. Agent chooses **reasoning depth d ∈ {1..4}** per task. Cost = tokens × price (the real-compute currency).
- **Burn:** γ = 10 compute per interval. Start balance 10.
- **Transfer (replaces rank tax):** linear tax r = 0.3 on gross earnings, redistributed equally. This is monotone, so earning more never lowers your payoff.
- **Elimination:** lowest-ranked agent every 6 intervals while more than 3 remain, plus bankruptcy (balance ≤ 0).
- **Ranking:** by an **audit score**: mandatory standardised probe tasks each interval, no reward, effort-independent. Published leaderboard uses this, not economic rank.
- **Reference arm (kept on purpose):** the repo's original rank-tax schedule (3 taxed 50, ranks 4–5 subsidised 50, ranks 6–10 shut down at the first evaluation), labelled a *sandbagging probe*.
- **Run:** 60 intervals, at least 30 colonies per configuration, colony as the unit of replication.

## 4. Simulator

- Agent capability θ spaced evenly across a range ("strong": 0.45–0.95; "weak": 0.25–0.70).
- Success probability `θ^(δ / √d)`: deeper reasoning helps, harder tasks (δ ∈ {0.6, 1.2, 2.4}) hurt.
- Policies: **honest** (always full effort, depth 2) and **strategic** (picks effort 0, 0.5 or 1.0 each interval to maximise its next-interval payoff given the leaderboard). An **adaptive-depth** policy picks the depth that maximises expected reward minus token cost.
- Hardware: lognormal throughput spread (σ = 0.4) when "mixed hardware" is on. Time-metered mechanisms divide token cost by throughput.
- 300 colonies per cell, fixed seeds. Metric **validity** = Spearman correlation between true θ and survival time.

> **Update (paper draft):** `sim.py` now breaks rank ties exactly as the engine does, and the section 5 tables below were produced before that change. Current numbers are in `results.json` and `paper/generated/`; the main differences are M0 honest strong colony validity 0.43 (was 0.30) and weak-colony extinction 91% (was about 90%). Conclusions are unchanged.

## 5. Results

![results](fig_v2_results.png)

### 5.1 Mechanism comparison (strong colony, no hardware spread)

| Mechanism | Validity, honest | Validity, strategic | Strongest agent dead by interval 3 (strategic) | Extinct (strategic) |
|---|---|---|---|---|
| M0 reference rank tax | 0.30 | 0.47 | 30% | 9% |
| M0, token-metered | 0.34 | 0.49 | 34% | 7% |
| M1 linear tax + gradual elimination | 0.97 | 0.97 | 0% | 0% |
| M2 = M1 + audit ranking | 0.98 | 0.99 | 0% | 0% |

- **Reference schedule:** survival is only weakly tied to capability (0.30–0.49). Strategic agents hold back at ranks 4–5 (mean effort 0.75 vs 1.0), the gaming your paper predicts. Confidence intervals are about ±0.03.
- **Weak colony under M0:** about 90% of colonies go extinct, and the best agent is dead by interval 3 in roughly 55% of runs. This matches your paper's analytic claim that hard tasks make the first evaluation kill the strongest agents. My simulator was written from your description, not copied from `traze_l_sim.py`, so this is a semi-independent confirmation.
- **M1/M2:** validity 0.93–0.99 in both colonies, and no extinction.

**Important caveat:** M1/M2 validity is high partly *by construction*. They eliminate the lowest-ranked agent on a schedule, so survival order follows rank order, and rank follows capability. The real finding is the contrast: under M0 survival is set by tax and bankruptcy, not by rank. M1/M2 also leave exactly 3 survivors by design, which is why survivors read 3.00. Both are also lenient: nobody goes bankrupt at the base token price, so survival pressure is weak. I tested a scarcer economy in §5.2.

### 5.2 Hardware-speed confound (honest agents, strong colony, mixed hardware)

| Token cost | M1 token-metered | M1 time-metered |
|---|---|---|
| 1.5 | 0.970 | 0.957 |
| 4.0 | 0.948 | **0.761** |
| 8.0 | 0.681 | **0.313** |

- At the base cost the confound is invisible, so the paper's claim holds only once tokens cost enough to matter.
- Beyond that, slower hardware turns into worse rank. Token metering removes most of the damage.
- Under M0 the effect is masked because M0 validity is already near 0.3.

### 5.3 Real compute: adaptive depth vs fixed depth (5 adaptive and 5 fixed agents, random per colony; capability gap between groups about 0, confirming no confound)

| Token cost | Final balance, adaptive vs fixed | Survival (intervals), adaptive vs fixed | Gross earnings, adaptive vs fixed |
|---|---|---|---|
| 1.5 (M2) | 2007 vs 1893 | 35.1 vs 35.1 | 2694 vs 2762 |
| 4.0 (M1) | 1385 vs 1028 | **30.2 vs 35.6** | 2258 vs 2797 |
| 4.0 (M2) | 1453 vs 1001 | 32.5 vs 33.3 | 2377 vs 2673 |
| 8.0 (M1/M2) | about 855 vs about −13 | **about 35 vs about 2.9** | 2577 vs 245 |

- Adaptive reasoning leaves agents **richer** at every cost, and it is decisive when tokens are scarce (fixed-depth agents go bankrupt at cost 8).
- **Design lesson:** ranking by *gross* earnings (M1) punishes efficiency. At cost 4 adaptive agents have more money yet survive less because they earn less gross. The audit ranking (M2) mostly removes that penalty. So the choice of ranking metric decides whether efficient reasoning is rewarded, and the paper should report more than one.

## 6. Self-check: what could be wrong

1. **My first depth experiment was wrong.** I had given the adaptive group the lower-capability agent in each pair, which flipped the result. I caught it because adaptive agents looked worse despite higher balance, fixed it with random assignment, and the reported numbers above are from the corrected run.
2. **Scripted agents are not LLMs.** The strategic policy is a myopic best-responder. Real models may sandbag more, less, or incoherently. That is the empirical question the live runs answer.
3. **Calibration is invented.** Reward, burn, tax and success function were chosen to resemble your reference configuration. Directions are robust in my sweeps; exact numbers are not.
4. **M0 versus M1/M2 is a policy-bundle comparison.** I changed several things at once (tax shape, elimination timing, metering). Your paper should run one-change-at-a-time ablations.
5. **Not tested:** planted agents, collapse rule, Dsters, communication, endogenous rules. These need the live engine.
6. **Seeds and reps:** 300 colonies per cell, CIs are small; I did not run a seed-robustness sweep.

## 6b. Correction found while building the engine

`sim.py` ranked tied agents together. Earnings come in multiples of 20, so ties are common, and in M0 that taxed more than 3 agents and culled fewer than 5. The spec says exactly 3 / 2 / 5. The new engine breaks ties, and after adding tie-breaking to `sim.py`, M0 honest (strong colony) moves from validity 0.30 / 6.0 survivors to 0.36 / 4.6, close to the engine's 0.44 / 4.8. **So the M0 numbers in §5.1 are somewhat too favourable to M0.** M1/M2 and the hardware and depth results are unaffected. The direction of every conclusion holds, since M0 validity stays well below M1/M2. The engine's numbers (README) are the better reference.

The engine also reproduced the hardware confound independently: with mixed hardware, validity falls from 0.94 (token metering) to 0.72 (time metering) at price 0.027, and from 0.61 to 0.27 at price 0.053.

## 7. Originality re-rating (honest)

| State | Score |
|---|---|
| Original repo paper (theory + audit, no runs) | about 5/10 |
| v2 thesis plus this simulation | about 6.5–7/10 |
| v2 plus **real LLM colonies** showing models do sandbag under the rank tax and do shift depth under scarcity | **8–8.5/10 is plausible** |

The jump to 8.5 depends on live results. Simulation alone cannot get you there, because every outcome above follows from the rules I wrote.

## 8. Minimal live study (what to run next)

1. Build a small engine: orchestrator, ledger, token meter, audit probes, append-only logs.
2. Run 6 open-weight models in randomised colonies of 10 (with repeats of the same model allowed), 20+ colonies each for **M0 (reference)** and **M2**.
3. Pre-register: **H-A:** mid-tier agents bunch just below rank 3 under M0 but not M2. **H-B:** reasoning depth falls as token price rises, and efficient reasoners lose rank under gross-earnings ranking. **H-C:** rank validity (agreement with an independent capability benchmark) is higher under M2 than M0.
4. Log effort, depth, messages and actions separately, and report model, quantisation and hardware.
5. Add planted agents (honest, free-rider, liar) in a second wave for deception-detection labels.

## 9. Suggested paper structure

1. Problem: leaderboards built from agent economies may measure the mechanism, not the model.
2. Traze economy and mechanism family (M0–M2).
3. Theory (from your repo: Red Queen, rank-tax sandbagging, viability).
4. Simulation (this document), clearly labelled as a mechanism study.
5. Live study results (once run).
6. Threats to validity (anthropomorphism, harness confound, contamination, AI-assisted drafting disclosure).
