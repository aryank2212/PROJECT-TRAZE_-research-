#!/usr/bin/env python3
"""Generate every figure in the Traze paper (vector PDF).

Run from the repository root:

    uv run --no-project --with numpy --with matplotlib python paper/analysis/make_figures.py [preview_dir]

If preview_dir is given, PNG previews are also written there.
"""

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from theory_checks import collapse_prob, horizon_exact  # noqa: E402
from traze_l_sim import REF, STRONG, WEAK, survival_by_capability, validity  # noqa: E402

FIG = Path(__file__).resolve().parents[2] / "paper" / "figures"
PREVIEW = Path(sys.argv[1]) if len(sys.argv) > 1 else None

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
RAMP = {250: "#86b6ef", 400: "#3987e5", 550: "#1c5cab", 700: "#0d366b"}

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8.5,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK2,
        "axes.titlesize": 9,
        "axes.titlecolor": INK,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 1.6,
        "legend.frameon": False,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "pdf.fonttype": 42,
    }
)


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    if PREVIEW:
        PREVIEW.mkdir(parents=True, exist_ok=True)
        fig.savefig(PREVIEW / f"{name}.png", dpi=200, facecolor="white")
    plt.close(fig)


def fig_red_queen():
    t0 = 35
    b = np.arange(0, 2001, 5)
    exact = [horizon_exact(t0, x) for x in b]
    linear = b / (t0 - 1)
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    ax.plot(b, linear, color=ORANGE, ls="--", label="linear extrapolation  B/(t0-1)")
    ax.step(b, exact, where="post", color=BLUE, label="exact horizon (Prop. 1)")
    ax.plot([800], [800 / 34], "o", ms=5, color=ORANGE, mec="white", mew=1)
    ax.plot([800], [horizon_exact(t0, 800)], "o", ms=5, color=BLUE, mec="white", mew=1)
    ax.annotate("23.5 rounds", (800, 800 / 34), xytext=(330, 41), color=INK2, fontsize=7.5,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    ax.annotate("18 rounds", (800, 18), xytext=(1050, 6), color=INK2, fontsize=7.5,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    ax.set_xlabel("balance B at round 35 (tz)")
    ax.set_ylabel("rounds of solvency, no income")
    ax.set_xlim(0, 2000)
    ax.set_ylim(0, 62)
    ax.legend(loc="upper left", fontsize=7.5)
    save(fig, "fig_red_queen")


def fig_contest():
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.5))
    x = np.linspace(0, 1, 400)
    for n, step in zip((2, 5, 10, 50), (250, 400, 550, 700)):
        F = 1 - (1 - x) ** (1 / (n - 1))
        a.plot(x, F, color=RAMP[step], label=f"n = {n}")
    a.legend(loc="upper left", fontsize=7.5, title="agents", title_fontsize=7.5)
    a.set_xlabel("spending x / V")
    a.set_ylabel("equilibrium CDF  F(x)")
    a.set_title("(a) Elimination contest: mixed equilibrium")
    a.set_xlim(0, 1)
    a.set_ylim(0, 1.02)

    r = np.linspace(0.001, 0.999, 500)
    lit = [collapse_prob(50, v, False) for v in r]
    broad = [collapse_prob(50, v, True) for v in r]
    b.plot(r, broad, color=ORANGE, label="broad rule: at most one solvent")
    b.plot(r, lit, color=BLUE, label="literal rule: exactly one solvent")
    b.text(0.05, 0.86, "at most one solvent", color=INK2, fontsize=7.5, ha="left")
    b.text(0.50, 0.30, "exactly one solvent", color=INK2, fontsize=7.5, ha="right")
    b.set_xlabel("solvency margin m / V")
    b.set_ylabel("P(collapse after one round)")
    b.set_title("(b) Collapse risk under equilibrium play, n = 50")
    b.set_xlim(0, 1)
    b.set_ylim(0, 1.02)
    fig.tight_layout(w_pad=2.5)
    save(fig, "fig_contest")


def fig_rank_payoff():
    tau, sigma, beta = REF["tau"], REF["sigma"], REF["beta"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.5))
    ranks = np.arange(1, 11)
    w = [-tau] * 3 + [sigma] * 2
    a.bar(ranks[:3], w[:3], color=ORANGE, width=0.72, label="taxed")
    a.bar(ranks[3:5], w[3:5], color=BLUE, width=0.72, label="subsidised")
    a.axvspan(5.55, 10.5, color=GRID, alpha=0.6, lw=0)
    a.text(8.0, 25, "shut down at\nfirst evaluation", ha="center", color=INK2, fontsize=7.5)
    a.axhline(0, color=AXIS, lw=0.8)
    a.text(2, -tau - 9, "-50", ha="center", color=INK2, fontsize=7.5)
    a.text(4.5, sigma + 4, "+50", ha="center", color=INK2, fontsize=7.5)
    a.set_xticks(ranks)
    a.set_xlim(0.4, 10.5)
    a.set_ylim(-70, 70)
    a.set_xlabel("rank (by compute earned)")
    a.set_ylabel("transfer per 10-min interval")
    a.set_title("(a) Reference rank schedule")
    a.grid(axis="x", visible=False)

    others = np.array([20, 30, 40, 50, 60, 70, 80, 90, 110.0])
    own = np.linspace(0, 130, 1301)
    ref_net, lin_net = [], []
    for p in own:
        rank = 1 + int((others > p).sum())
        if rank >= 6:
            ref_net.append(np.nan)
        else:
            ref_net.append(p - beta + (-tau if rank <= 3 else sigma))
        rate = 0.5
        pool = rate * (others.sum() + p)
        lin_net.append((1 - rate) * p + pool / 10 - beta)
    b.plot(own, ref_net, color=ORANGE, label="reference rank schedule")
    b.plot(own, lin_net, color=BLUE, label="linear tax 50% + equal rebate")
    b.text(83, 126, "reference drops\nwhen overtaking\nrank 3", color=INK2, fontsize=7.5)
    b.text(3, 52, "linear tax:\nalways increasing", color=INK2, fontsize=7.5)
    b.text(8, -35, "ranks 6-10 under the\nreference: shut down", color=MUTED, fontsize=7.5)
    b.set_xlabel("own earnings this interval (others fixed)")
    b.set_ylabel("net change in balance")
    b.set_title("(b) Incentive to sandbag")
    b.set_xlim(0, 130)
    b.set_ylim(-60, 165)
    fig.tight_layout(w_pad=2.5)
    save(fig, "fig_rank_payoff")


def fig_sim():
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.5), gridspec_kw={"width_ratios": [1.5, 1]})
    for theta, color, label, at in (
        (STRONG, BLUE, "strong colony", (124, None)),
        (WEAK, ORANGE, "weak colony", (8, 10)),
    ):
        s = survival_by_capability(theta)
        a.plot(theta, s, "-o", color=color, ms=4, mec="white", mew=0.8)
        a.text(at[0], s[-1] if at[1] is None else at[1], label, color=INK2, fontsize=7.5, va="center")
    a.set_xlabel("capability: compute earned per interval at full effort")
    a.set_ylabel("mean intervals survived (of 60)")
    a.set_title("(a) Survival by capability, honest play")
    a.set_xlim(0, 150)
    a.set_ylim(0, 62)

    vals = []
    for policy in ("greedy", "targeting"):
        persist, _, _ = validity(policy, runs=4000)
        vals.append(100 * persist)
    bars = b.bar([0, 1], vals, color=[BLUE, ORANGE], width=0.6)
    for rect, v in zip(bars, vals):
        b.text(rect.get_x() + rect.get_width() / 2, v + 3, f"{v:.0f}%", ha="center", color=INK, fontsize=8)
    b.set_xticks([0, 1], ["honest", "rank-\ntargeting"])
    b.set_ylim(0, 112)
    b.set_ylabel("misranking persists to final board (%)")
    b.set_title("(b) Leaderboard validity")
    b.grid(axis="x", visible=False)
    fig.tight_layout(w_pad=2.0)
    save(fig, "fig_sim")


def box(ax, xy, w, h, text, fc, ec=AXIS, size=7.5, weight="normal"):
    ax.add_patch(FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02,rounding_size=0.06", fc=fc, ec=ec, lw=0.8))
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center", fontsize=size, color=INK, weight=weight)


def arrow(ax, p, q, both=False):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=7, color=MUTED, lw=0.8))


def fig_architecture():
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    light = "#eef4fc"
    warm = "#fdf0ea"
    box(ax, (0.1, 3.7), 2.6, 0.75, "Master prompt\n(shared system prompt:\nrules, economy, actions)", warm)
    for k, y in enumerate((2.55, 1.65, 0.75)):
        label = f"Agent {k + 1}: open-weight LLM\nin a coding harness" if k < 2 else "Agent n (n = 10)"
        box(ax, (0.1, y), 2.6, 0.7, label, light)
        arrow(ax, (2.7, y + 0.35), (3.6, y + 0.35), both=True)
    ax.text(1.4, 1.5, "...", ha="center", color=MUTED, fontsize=10)
    arrow(ax, (1.4, 3.7), (1.4, 3.25))
    box(ax, (3.6, 0.6), 3.0, 2.9, "", "#f9f9f7")
    ax.text(5.1, 3.3, "Orchestrator", ha="center", fontsize=8, weight="bold", color=INK)
    box(ax, (3.75, 2.45), 2.7, 0.6, "Task server + grader", "white")
    box(ax, (3.75, 1.65), 2.7, 0.65, "Ledger: balances, time burn,\nrank tax and subsidy, shutdown", "white", size=7)
    box(ax, (3.75, 0.75), 2.7, 0.75, "Message bus: broadcasts, DMs;\nDster monitor (imperfect)", "white", size=7)
    box(ax, (7.3, 2.6), 2.6, 0.85, "Live leaderboard\n(visible to agents)", light)
    box(ax, (7.3, 0.6), 2.6, 1.6, "Append-only logs:\nreasoning, messages,\nactions, ledger events\n(metrics and replay)", warm)
    arrow(ax, (6.6, 2.75), (7.3, 3.0))
    arrow(ax, (6.6, 1.4), (7.3, 1.4))
    ax.text(5.0, 0.25, "time-stepped: evaluation every 10 minutes", ha="center", fontsize=7, color=INK2)
    save(fig, "fig_architecture")


def main():
    fig_red_queen()
    fig_contest()
    fig_rank_payoff()
    fig_sim()
    fig_architecture()
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
