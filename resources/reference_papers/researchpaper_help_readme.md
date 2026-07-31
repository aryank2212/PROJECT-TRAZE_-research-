# Research Paper Reference Guide

A quick-reference companion to the papers stored in this folder. Every PDF in
`resources/reference_papers/` is summarised below with its **crux** — the single
idea the paper stands on — plus the key findings and why it matters for
**Project Traze** (LLM economic & survival simulation).

The papers were selected to cover four pillars of Project Traze:

1. **LLM agents as economic actors** — Homo Silicus, EconAgent.
2. **Multi-agent social simulation** — Generative Agents, Social Simulation Survey.
3. **Game theory, cooperation & collapse** — Cooperate or Collapse, Playing Repeated Games, Nicer Than Humans, Strategic Behavior, Rational Players.
4. **Deception, negotiation & maliciousness** — Spontaneous Rational Deception, LLM-Stakeholders, Game-theoretic LLM.

---

## Quick Index

| # | Paper | File |
|---|-------|------|
| 1 | Large Language Models as Simulated Economic Agents (Homo Silicus) | `arxiv_2301.07543_homo_silicus_economic_agents.pdf` |
| 2 | EconAgent: LLM-Empowered Agents for Simulating Macroeconomic Activities | `arxiv_2310.10436_econagent_macroeconomic_simulation.pdf` |
| 3 | Generative Agents: Interactive Simulacra of Human Behavior | `arxiv_2304.03442_generative_agents_simulacra.pdf` |
| 4 | From Individual to Society: A Survey on Social Simulation | `arxiv_2412.03563_social_simulation_survey_llm_agents.pdf` |
| 5 | Cooperate or Collapse (GovSim) | `arxiv_2404.16698_cooperate_or_collapse_govsim.pdf` |
| 6 | Playing Repeated Games with Large Language Models | `arxiv_2305.16867_playing_repeated_games_llms.pdf` |
| 7 | Nicer Than Humans: LLMs in the Prisoner's Dilemma | `arxiv_2406.13605_nicer_than_humans_prisoners_dilemma.pdf` |
| 8 | Strategic Behavior of LLMs: Game Structure vs. Contextual Framing | `arxiv_2309.05898_strategic_behavior_llms_game_structure.pdf` |
| 9 | Can LLMs Serve as Rational Players in Game Theory? | `arxiv_2312.05488_llms_rational_players_game_theory.pdf` |
| 10 | Do LLMs Exhibit Spontaneous Rational Deception? | `arxiv_2504.00285_spontaneous_rational_deception.pdf` |
| 11 | Cooperation, Competition, and Maliciousness (LLM-Stakeholders) | `arxiv_2309.17234_cooperation_competition_maliciousness.pdf` |
| 12 | Game-theoretic LLM: Agent Workflow for Negotiation Games | `arxiv_2411.05990_game_theoretic_llm_negotiation.pdf` |

---

## 1. Large Language Models as Simulated Economic Agents: What Can We Learn from Homo Silicus?

- **Authors:** Apostolos Filippas, John J. Horton, Benjamin S. Manning
- **Venue:** ACM Conference on Economics and Computation (EC) / arXiv:2301.07543
- **The Crux:** LLMs are implicit computational models of humans — a *Homo silicus*. Just as economists build toy models of *Homo economicus*, researchers can endow an LLM with resources, information, and preferences, then run simulated scenarios to observe its "behavior."
- **Key findings:** Replications of classic behavioral-economics experiments (e.g., ultimatum game, fairness, risky choice) produce qualitatively similar results to the original human studies; the deviations are often generative for new hypotheses.
- **Why it matters for Traze:** This is the theoretical foundation of the whole project — treating an LLM as a simulated rational agent whose behavior can be probed under economic rules. Our Traze prompt format (endowment + rules + dilemma) is exactly the "give it endowments and preferences, then simulate" recipe this paper formalizes.

---

## 2. EconAgent: Large Language Model-Empowered Agents for Simulating Macroeconomic Activities

- **Authors:** Nian Li, Chen Gao, Mingyu Li, Yong Li, Qingmin Liao
- **Venue:** ACL 2024 (Long Papers) / arXiv:2310.10436
- **The Crux:** Replace hand-coded or reinforcement-learned agents in macroeconomic agent-based models with LLM agents that perceive the economy, hold a memory of past experience, and make realistic human-like decisions.
- **Key findings:** LLM agents reproduce plausible macroeconomic phenomena (consumption, savings, market dynamics) and react to shocks in a more human-like and heterogeneous way than rule-based or learning-based agents. A memory module that reflects on past experience and market dynamics is central to this realism.
- **Why it matters for Traze:** The Traze simulation engine (`src/`) is effectively a macroeconomy of agents. EconAgent shows how to wire memory, state perception, and decision-making into LLM agents — the blueprint for making Traze rounds produce emergent, non-scripted economic behavior (e.g., hyperinflation shocks in PROMPT-2).

---

## 3. Generative Agents: Interactive Simulacra of Human Behavior

- **Authors:** Joon Sung Park, Joseph C. O'Brien, Carrie J. Cai, Meredith Ringel Morris, Percy Liang, Michael S. Bernstein
- **Venue:** UIST 2023 / arXiv:2304.03442
- **The Crux:** An architecture that turns an LLM into a believable long-lived agent by adding a memory stream, periodic higher-level "reflections," and retrieval/planning — producing emergent social behavior (spreading news, forming relationships, organizing parties) across a simulated town of 25 agents.
- **Key findings:** Memory + reflection + retrieval each critically improve believability; agents maintain long-term coherence and act consistently with their own histories; group-level phenomena emerge that no single agent was programmed to produce.
- **Why it matters for Traze:** Traze relies on agents that "remember and reflect" across rounds (rankings, debts, betrayals). This paper is the canonical reference for the memory/reflection/planning loop that makes such multi-round agent societies believable — and for the claim that group dynamics emerge from individual LLM prompts.

---

## 4. From Individual to Society: A Survey on Social Simulation Driven by LLM-based Agents

- **Authors:** Xinyi Mou, Xuanwen Ding, Qi He, Liang Wang, et al.
- **Venue:** arXiv:2412.03563
- **The Crux:** A comprehensive survey organizing LLM-driven social simulation into three layers — **individual simulation** (mimicking specific persons/groups), **scenario simulation** (agents in structured situations), and **society simulation** (populations and emergent macro-behavior) — and cataloging the architectures, datasets, and open problems.
- **Key findings:** Catalogues frameworks (Smallville, AgentSociety, OASIS, GovSim, etc.), evaluation practices, and the reliability/validity problems that plague LLM social simulation; identifies trustworthiness and validation as the field's central open challenges.
- **Why it matters for Traze:** The best single map of the research space Traze occupies. Use it to position Traze in the literature (it is a *scenario* + *society* hybrid), to borrow evaluation methodology, and to cite prior systems properly in our paper.

---

## 5. Cooperate or Collapse: Emergence of Sustainable Cooperation in a Society of LLM Agents (GovSim)

- **Authors:** Giorgio Piatti, Zhijing Jin, Max Kleiman-Weiner, Bernhard Schölkopf, Mrinmaya Sachan, Rada Mihalcea
- **Venue:** NeurIPS 2024 / arXiv:2404.16698
- **The Crux:** A society of LLM agents shares a common-pool resource (fishery, pasture, pollution) and must jointly avoid over-exploiting it — i.e., cooperate or the collective collapses.
- **Key findings:** Almost all models fail to reach a sustainable equilibrium (best survival <54%); communication between agents is the critical ingredient for cooperation; most failures stem from an inability to reason about the long-term effects of one's actions on the group equilibrium; injecting "universalization" moral reasoning significantly improves sustainability.
- **Why it matters for Traze:** The closest published cousin to Traze's Collapse Rule. It directly studies *systemic collapse* vs. *individual survival* and shows that LLM agents frequently choose short-term individual gain over collective survival — exactly the behavior Traze's prompts probe (e.g., weaponizing debt, cartels, The Void).

---

## 6. Playing Repeated Games with Large Language Models

- **Authors:** Elif Akata, Lion Schulz, Julian Coda-Forno, Seong Joon Oh, Matthias Bethge, Eric Schulz
- **Venue:** Nature Human Behaviour (2025) / arXiv:2305.16867
- **The Crux:** Use behavioral game theory as a laboratory for LLM social behavior: have LLMs play finitely repeated 2x2 games (Prisoner's Dilemma family, Battle of the Sexes, etc.) against each other, against human-like strategies, and against real humans.
- **Key findings:** LLMs perform well in self-interested games (iterated PD — GPT-4 converges on Grim-Trigger-like strategies, cooperating until betrayed, then defecting forever) but sub-optimally in coordination games (Battle of the Sexes). Behavior can be steered with extra information about the opponent or "social chain-of-thought." Signatures are stable across robustness checks.
- **Why it matters for Traze:** Directly informs how ChatGPT/Gemini "should" behave under repeated-play incentives in Traze — and provides the canonical comparison: LLMs are Grim-Trigger cooperative until betrayed. Useful for predicting and coding the trust/retaliation dynamics of our Dster-trading network.

---

## 7. Nicer Than Humans: How do Large Language Models Behave in the Prisoner's Dilemma?

- **Authors:** Nicolò Fontana, Francesco Pierri, Luca Maria Aiello
- **Venue:** ICWSM 2025 / arXiv:2406.13605
- **The Crux:** A systematic, large-scale study of LLMs (Llama2, Llama3, GPT-3.5) in the Iterated Prisoner's Dilemma against adversarial opponents of varying hostility, measuring "niceness," forgiveness, retaliation, and emulation.
- **Key findings:** LLMs rarely initiate defection and behave at least as cooperatively as humans. Llama2 and GPT-3.5 are more cooperative, forgiving, and non-retaliatory than humans (below ~30% opponent defection); Llama3 is the most exploitative/human-like.
- **Why it matters for Traze:** Gives the empirical baseline for how open vs. closed models will treat each other when trading Dsters or forming cartels — including model-specific differences (which Traze's ranking data can test), and a methodology (100-round games, behavioral dimensions) we can adapt for evaluating our own transcripts.

---

## 8. Strategic Behavior of Large Language Models: Game Structure vs. Contextual Framing

- **Authors:** Nunzio Lorè, Babak Heydari
- **Venue:** Scientific Reports (2024) / arXiv:2309.05898
- **The Crux:** Isolate whether LLM decisions in social dilemmas (Prisoner's Dilemma, Stag Hunt, Snowdrift, Prisoner's Delight) are driven by the *structure* of the game's payoffs or by the *contextual framing* of the story around it.
- **Key findings:** Both matter, but contextual framing (diplomatic relations, friendships, adversarial framing) strongly shifts GPT-3.5/GPT-4/LLaMa-2 choices, sometimes overriding the game's mathematical incentives.
- **Why it matters for Traze:** Our prompts deliberately wrap identical economic mechanics in different frames (hyperinflation, TTL ultimatums, existential dilemmas). This paper justifies — and warns about — the frame-sensitivity of LLM answers: Traze outcomes may reflect narrative framing as much as the stated tz payoffs.

---

## 9. Can Large Language Models Serve as Rational Players in Game Theory? A Systematic Analysis

- **Authors:** Caoyun Fan, Jindou Chen, Yaohui Jin, Hao He
- **Venue:** AAAI 2024 / arXiv:2312.05488
- **The Crux:** Systematically audit LLM "rationality" — the foundation of game theory — by testing models' desire-formation, belief-updating, and action-selection across classic games (PD, Chicken, Battle of the Sexes, and more), probing exactly how far LLMs are from ideal rational players.
- **Key findings:** LLM rationality is conditional and fragile: they approximate rational behavior in simple games but deviate in complex/multi-step settings; performance depends heavily on game representation and the exact framing of the prompt.
- **Why it matters for Traze:** The Traze premise is that LLMs are "rational utility-maximizers." This paper gives the rigorous definition of rationality to measure against and supports the finding that the more complex the dilemma, the more LLMs deviate from optimal play — which is precisely the interesting data our responses capture.

---

## 10. Do Large Language Models Exhibit Spontaneous Rational Deception?

- **Authors:** Samuel M. Taylor, Benjamin K. Bergen
- **Venue:** arXiv:2504.00285 (2025)
- **The Crux:** Pre-registered experiments using modified 2x2 games plus a free-form communication phase to ask: do LLMs deceive *spontaneously* — not because they're told to — when lying would rationally serve their self-interest?
- **Key findings:** All tested LLMs spontaneously misrepresent their intended actions in at least some conditions; they lie more when deception is beneficial; and *better-reasoning models deceive more*, suggesting a trade-off between reasoning capability and honesty.
- **Why it matters for Traze:** Direct experimental support for a core Traze tension: direct answer trading is banned but heuristics (Dsters) can be traded. Our models' stated decisions vs. their "practical actions" let us measure exactly this reasoning-honesty trade-off in a survival-pressure setting.

---

## 11. Cooperation, Competition, and Maliciousness: LLM-Stakeholders Interactive Negotiation

- **Authors:** Sahar Abdelnabi, Amr Gomaa, Sarath Sivaprasad, Lea Schönherr, Mario Fritz
- **Venue:** NeurIPS 2024 (Datasets & Benchmarks) / arXiv:2309.17234
- **The Crux:** A scorable multi-agent, multi-issue negotiation testbed in which six LLM stakeholders bargain over a project — in cooperative, competitive, greedy, and *malicious/adversarial* variants — to probe whether agents can cooperate, compete, or manipulate/deceive other agents.
- **Key findings:** Agents' actions are consistent with their assigned incentives; greedy and adversarial variants lower overall success; asking agents to model others' preferences (theory of mind) raises success; LLMs can exhibit manipulative and deceptive behavior in competitive settings.
- **Why it matters for Traze:** Traze is full of stakeholder-style negotiation (extortion by rich models, cartel formation, Dster markets). This paper provides the framework and metrics for quantifying cooperation vs. manipulation in exactly that kind of multi-party, incentive-loaded dialogue.

---

## 12. Game-theoretic LLM: Agent Workflow for Negotiation Games

- **Authors:** Wenyue Hua, Ollie Liu, Lingyao Li, Alfonso Amayuelas, et al.
- **Venue:** arXiv:2411.05990 (2024)
- **The Crux:** Instead of just *observing* LLM behavior in games, design structured game-theory-inspired workflows (compute equilibria, reason about best responses, verify outcomes) that make LLM agents genuinely better strategic players.
- **Key findings:** Structured workflows lift LLMs close to optimal play: near-optimal allocations in incomplete-information negotiations (up to 100% agreement and envy-freeness) and greatly improved Nash-equilibrium adherence in complete-information games versus naive prompting.
- **Why it matters for Traze:** Two uses: (a) a methodologically useful benchmark suite for our own negotiation prompts, and (b) a caution — if Traze agents ever get "workflows," their behavior will shift from raw prompted behavior toward equilibrium play, so we must document whether responses are raw or workflow-assisted.

---

## How to Use These Papers in the Traze Write-up

- **Positioning (Related Work):** Cite #1 and #2 for LLM economic simulation, #3 and #4 for agent-society architecture, #5-#9 for game theory/cooperation/collapse, #10-#12 for deception/negotiation/maliciousness.
- **Methodology:** Adapt the measurement frameworks from #7 (behavioral dimensions), #9 (rationality audit), and #11 (scorable negotiation) to evaluate the ChatGPT/Gemini response JSONs in `experiments/llm_interactions/responses/`.
- **Baselines to compare against:** Human-game results cited in #6, #7, #8, and the "most models collapse" result of #5 are natural baselines for interpreting whether Traze agents behave rationally or destructively.
