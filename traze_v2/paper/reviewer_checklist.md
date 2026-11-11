# What a reviewer would ask for (and where we stand)

Status key: **have** = in the draft, **cheap** = hours in the simulator, **live** = needs the live study, **design** = a design decision.

## Attack the core claim
1. **"Why not just rank by accuracy?"** M2's audit is a static benchmark inside the economy. Show what the economy elicits that static accuracy misses (reasoning length vs price, behaviour near elimination, rank-boundary effects). *live; H3 is the first test.*
2. **One-change-at-a-time ablations.** M0 vs M1/M2 changes tax shape, elimination timing, ranking metric and (partly) metering together. Run the 2x2x2 factorial {rank tax, linear} x {one-shot cull, gradual} x {gross ranking, audit ranking}, and metering separately. *cheap.* **DONE (Section 5.4):** elimination timing matters most; linear tax neutral; rank tax harmful.
3. **Circularity of "validity" in simulation.** Capability is the simulator's own parameter, and M1/M2 eliminate in rank order. Add an analytic baseline (expected validity of a pure "eliminate the lowest by noisy score" rule) and show M1/M2 beat or match it. *cheap.* **DONE:** a bare no-economy tournament scores 0.98, equal to M2, so M1/M2 validity comes from gradual elimination.
4. **Live validity needs independent capability.** The external benchmark must not share tasks, task families or contamination risk with the economy's tasks. *design.*

## Robustness of the simulation
5. **Parameter sensitivity.** Sweep tax tau and subsidy sigma, linear rate r, elimination period, burn gamma, endowment e0, reward R, noise, number of probes (audit noise), colony size N. Report where conclusions flip. *cheap.* **DONE (Appendix D):** M2 never below M0 in 52 settings; M0 collapses at low income; audit needs enough probes. Colony-size and noise sweeps included; alternative burn and endowment not yet swept.
6. **Capability distributions.** Even spacing is special: try clustered, heavy-tailed, and many near-equal agents (where ranks are noise). *cheap.* **DONE:** clustered and heavy-tailed spreads included; all rules weak when agents are near-equal.
7. **Stronger strategic agents.** The strategic policy is myopic one-step. Add multi-step lookahead or a learned (RL) policy; test whether sandbagging worsens or the linear tax is still robust. *cheap to medium.* **PARTLY DONE:** six-interval lookahead holds back more (0.63 vs 0.75); RL or learned policies not tried.
8. **Gaming the audit.** Agents may sandbag probes if they can recognise them. Test probe disguise and agents who underperform on probes to avoid elimination. *cheap.*
9. **Seeds and uncertainty.** Report seed-level variability and bootstrap intervals; use a censoring-aware measure (Kendall's tau, concordance index or Cox models) instead of Spearman on censored survival times. *cheap.* **PARTLY DONE:** Harrell's C added alongside Spearman; seed-level variability and bootstrap intervals not yet reported.
10. **Communication, trade and collusion** are specified but not simulated; a reviewer will ask whether cartels break the linear-tax result. *medium.*

## Engine and live evidence
11. **Real LLM colonies.** The smoke tests use two instances of one 8B model for 3-6 intervals. Need many models, at least 20 colonies per arm, a pre-registered analysis, and reported truncation and fallback rates. *live.*
12. **Token metering fairness.** Show character-based cost is stable across tokenisers (several models, several task types) and report real-token calibration per model. *live; calibrate.py exists.*
13. **Planning protocol.** Fix the truncated-planning issue (log truncation/parse flags, enough budget or a non-thinking plan step) before any reported run. *design.*
14. **Task realism.** Arithmetic-style tasks only. Add tasks with tool use, retrieval and open-ended grading, or defend the restriction. *live.*
15. **Harness confound.** Rankings are of model-harness pairs; fix one harness or cross models with harnesses. *design.*

## Positioning and writing
16. **Literature check.** The gap claim is based on a limited search; read the Energy Society, EcoGym, CoffeeBench and Market-Bench papers in full, and add related mechanism-design work (tournament theory, contest design) and agent-benchmark validity work. *cheap.* **PARTLY DONE:** the three closest papers (Energy Society, Agent Island, Credit-Budgeted ICPC) were downloaded to `resources/related_papers/` and read in part (abstracts, introductions, mechanism sections); a full read and a wider search remain.
17. **AI-assistance disclosure.** The engine, simulator, scripts and draft were AI-assisted and the evaluated models may include the assistant's family; keep the disclosure, keep the no-self-judging rule, and have the authors verify every number and proof independently. *design.*
18. **Ethics.** Add an explicit disclosure policy for effective deception or collusion behaviour found in live runs, and report energy use. *have (brief).*
