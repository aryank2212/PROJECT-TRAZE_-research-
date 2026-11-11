"""Generate every number and table used in the paper from results.json and runs/*.jsonl.

  python3 -I paper/make_tables.py        (run from traze_v2/)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "generated"
OUT.mkdir(exist_ok=True)
res = json.loads((ROOT / "results.json").read_text())
M, H, D = res["mechanisms"], res["hardware"], res["depth"]


def f2(x):
    return "--" if x is None else f"{x:.2f}"


def pct(x):
    return "--" if x is None else f"{100 * x:.0f}\\%"


# ---- Table: mechanisms ------------------------------------------------------------------
rows = []
for col, cname in (("strong", "Strong"), ("weak", "Weak")):
    for pol in ("honest", "strategic"):
        for mk, label in (("M0_reference", "M0 rank tax"), ("M1_linear", "M1 linear"),
                          ("M2_audit", "M2 audit")):
            v = M[f"{col}|{pol}|hw=0|{mk}"]
            rows.append(f"{cname} & {pol} & {label} & {f2(v['validity'])} $\\pm$ {f2(v['validity_ci'])}"
                        f" & {pct(v['best_dead_early'])} & {pct(v['extinct'])} & {f2(v['survivors'])} \\\\")
    rows.append("\\midrule")
rows.pop()
(OUT / "tab_mech.tex").write_text("\n".join(rows) + "\n")

# ---- Table: hardware confound -----------------------------------------------------------
rows = []
for cost in (1.5, 4.0, 8.0):
    g = lambda mk: H[f"cost={cost}|{mk}|hw=1"]
    rows.append(f"{cost} & {f2(g('M1_linear')['validity'])} $\\pm$ {f2(g('M1_linear')['validity_ci'])}"
                f" & {f2(g('M1_time')['validity'])} $\\pm$ {f2(g('M1_time')['validity_ci'])}"
                f" & {f2(g('M0t_tokens')['validity'])} & {f2(g('M0_reference')['validity'])} \\\\")
(OUT / "tab_hw.tex").write_text("\n".join(rows) + "\n")

# ---- Table: adaptive depth --------------------------------------------------------------
rows = []
for cost in (1.5, 4.0, 8.0):
    for mk, label in (("M1_linear", "M1 (gross)"), ("M2_audit", "M2 (audit)")):
        v = D[f"cost={cost}|{mk}"]
        rows.append(f"{cost} & {label} & {v['adaptive_bal']:.0f} / {v['fixed_bal']:.0f}"
                    f" & {v['adaptive_surv']:.1f} / {v['fixed_surv']:.1f}"
                    f" & {v['adaptive_earn']:.0f} / {v['fixed_earn']:.0f} \\\\")
(OUT / "tab_depth.tex").write_text("\n".join(rows) + "\n")

# ---- Live smoke runs --------------------------------------------------------------------
PLAN_CAP = {"live1": None, "live2": 3000, "live3": 600}
rows, nums = [], []
for run in ("live1", "live2", "live3"):
    ev = [json.loads(l) for l in open(ROOT / "runs" / f"{run}.jsonl", encoding="utf-8")]
    llm = {i for i, n in enumerate(ev[0]["agents"]) if n.startswith("qwen")}
    tasks = [e for e in ev if e["kind"] == "task" and e["agent"] in llm]
    probes = [e for e in ev if e["kind"] == "probe" and e["agent"] in llm]
    plans = [e for e in ev if e["kind"] == "plan" and e["agent"] in llm]
    cfg = ev[0]["config"]
    ok = sum(e["correct"] for e in tasks)
    trunc = sum(bool(e.get("truncated")) for e in tasks)
    tcost = sum(e["cost"] for e in tasks)
    pcost = sum(p.get("cost", 0.0) for p in plans)
    share = "n/a" if run == "live1" else f"{100 * pcost / (pcost + tcost):.0f}\\%"
    cap = PLAN_CAP[run]
    ptr = "n/a" if cap is None else f"{sum(1 for p in plans if (p.get('provider_tokens') or 0) >= cap)}/{len(plans)}"
    pr_ok = sum(e["solved"] for e in probes)
    pr_n = len(probes) * cfg["probes_per_interval"]
    ch = sum(e["reasoning_chars"] for e in tasks if e.get("provider_tokens"))
    tk = sum(e["provider_tokens"] for e in tasks if e.get("provider_tokens"))
    rows.append(f"{run[-1]} & {cfg['intervals']} & {cfg['price_per_token']} & {ok}/{len(tasks)} & {trunc}"
                f" & {pr_ok}/{pr_n} & {share} & {ptr} & {ch / tk:.2f} \\\\")
(OUT / "tab_live.tex").write_text("\n".join(rows) + "\n")

# ---- Scalar macros used in the text -----------------------------------------------------
g = lambda k: M[k]
macros = {
    "ValM0StrongH": f2(g("strong|honest|hw=0|M0_reference")["validity"]),
    "ValM0StrongS": f2(g("strong|strategic|hw=0|M0_reference")["validity"]),
    "ValMOneStrong": f2(g("strong|honest|hw=0|M1_linear")["validity"]),
    "ValMTwoStrong": f2(g("strong|honest|hw=0|M2_audit")["validity"]),
    "ExtM0Weak": pct(g("weak|honest|hw=0|M0_reference")["extinct"]),
    "BestDeadM0Weak": pct(g("weak|honest|hw=0|M0_reference")["best_dead_early"]),
    "BestDeadM0StrongS": pct(g("strong|strategic|hw=0|M0_reference")["best_dead_early"]),
    "MidEffort": f2(g("strong|strategic|hw=0|M0_reference")["mid_effort"]),
    "HwTokFour": f2(H["cost=4.0|M1_linear|hw=1"]["validity"]),
    "HwTimeFour": f2(H["cost=4.0|M1_time|hw=1"]["validity"]),
    "HwTokEight": f2(H["cost=8.0|M1_linear|hw=1"]["validity"]),
    "HwTimeEight": f2(H["cost=8.0|M1_time|hw=1"]["validity"]),
}
(OUT / "numbers.tex").write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in macros.items()))
print("wrote", sorted(p.name for p in OUT.iterdir()))


# ======================= Ablation experiments (results_ablation.json) =======================
A = json.loads((ROOT / "results_ablation.json").read_text())
F, SW, LK = A["factorial"], A["sweeps"], A["lookahead"]
NAMES = {"none": "none", "rank": "rank tax", "linear": "linear tax"}
ELIM = {"cull": "one-shot cull", "gradual": "gradual"}
RANK = {"gross": "gross", "audit": "audit"}

rows = []
for tr in ("none", "rank", "linear"):
    for el in ("cull", "gradual"):
        for rb in ("gross", "audit"):
            lab = f"{tr}/{el}/{rb}"
            h, s = F[f"strong|honest|{lab}"], F[f"strong|strategic|{lab}"]
            rows.append(f"{NAMES[tr]} & {ELIM[el]} & {RANK[rb]} & {f2(h['validity'])} & {f2(h['cindex'])}"
                        f" & {f2(s['validity'])} & {f2(s['cindex'])} \\\\")
    rows.append("\\midrule")
b_h, b_s = F["strong|honest|baseline"], F["strong|strategic|baseline"]
rows.append(f"\\multicolumn{{3}}{{l}}{{no economy (bare tournament)}} & {f2(b_h['validity'])} & {f2(b_h['cindex'])}"
            f" & {f2(b_s['validity'])} & {f2(b_s['cindex'])} \\\\")
(OUT / "tab_factorial.tex").write_text("\n".join(rows) + "\n")

# ---- sweeps appendix table ---------------------------------------------------------------
order = ["tau=sigma", "linear_r", "elim_every", "probes", "k_tasks", "reward", "n_agents", "spread"]
LABEL = {"tau=sigma": "$\\tau=\\sigma$", "linear_r": "linear rate $r$", "elim_every": "elimination period",
         "probes": "audit probes / interval", "k_tasks": "paid tasks / interval", "reward": "reward $R$",
         "n_agents": "colony size $n$", "spread": "capability spread"}
rows, gaps, flips, m1_gt_m2 = [], [], [], []
seen = {}
for key in SW:
    seen.setdefault(key.split("|")[0], None)
by_name = {}
for setting in seen:
    nm, val = setting.split("=", 1) if not setting.startswith("tau=sigma") else ("tau=sigma", setting.split("=", 2)[2])
    by_name.setdefault(nm, []).append((val, setting))
for nm in order:
    ents = sorted(by_name[nm], key=lambda e: (float(e[0]) if e[0].replace(".", "").isdigit() else 0))
    for val, setting in ents:
        cells = []
        for pol in ("honest", "myopic"):
            v = [SW[f"{setting}|{pol}|{s}"]["validity"] for s in ("rank/cull/gross", "linear/gradual/gross", "linear/gradual/audit")]
            cells += [f2(x) for x in v]
            gaps.append(v[2] - v[0]); flips.append(v[2] >= v[0]); m1_gt_m2.append((setting, pol, v[1] > v[2]))
        rows.append(f"{LABEL[nm]} = {val} & " + " & ".join(cells) + " \\\\")
    rows.append("\\midrule")
rows.pop()
(OUT / "tab_sweeps.tex").write_text("\n".join(rows) + "\n")
m1better = sorted({s for s, p, b in m1_gt_m2 if b and s.startswith("probes")})

abl = {
    "ValBaseline": f2(b_h["validity"]),
    "CindexBaseline": f2(b_h["cindex"]),
    "ValNoneGradAudit": f2(F["strong|honest|none/gradual/audit"]["validity"]),
    "ValLinCullGross": f2(F["strong|honest|linear/cull/gross"]["validity"]),
    "ValLinGradGross": f2(F["strong|honest|linear/gradual/gross"]["validity"]),
    "ValLinGradAudit": f2(F["strong|honest|linear/gradual/audit"]["validity"]),
    "ValRankGradGrossS": f2(F["strong|strategic|rank/gradual/gross"]["validity"]),
    "ValRankGradGrossH": f2(F["strong|honest|rank/gradual/gross"]["validity"]),
    "ValRankGradAuditH": f2(F["strong|honest|rank/gradual/audit"]["validity"]),
    "ValWeakRankGradAudit": f2(F["weak|honest|rank/gradual/audit"]["validity"]),
    "ExtWeakRankGradAudit": pct(F["weak|honest|rank/gradual/audit"]["extinct"]),
    "CindexMZeroH": f2(F["strong|honest|rank/cull/gross"]["cindex"]),
    "CindexMTwoH": f2(F["strong|honest|linear/gradual/audit"]["cindex"]),
    "MidEffMyopic": f2(LK["strong|myopic|rank/cull/gross"]["mid_effort"]),
    "MidEffLook": f2(LK["strong|lookahead|rank/cull/gross"]["mid_effort"]),
    "BestDeadLook": pct(LK["strong|lookahead|rank/cull/gross"]["best_dead_early"]),
    "BestDeadMyopic": pct(LK["strong|myopic|rank/cull/gross"]["best_dead_early"]),
    "ValLookM0": f2(LK["strong|lookahead|rank/cull/gross"]["validity"]),
    "ValLookMTwo": f2(LK["strong|lookahead|linear/gradual/audit"]["validity"]),
    "SweepSettings": str(len(flips)),
    "SweepFlips": str(sum(1 for x in flips if not x)),
    "SweepMinGap": f2(min(gaps)),
    "SweepMedGap": f2(sorted(gaps)[len(gaps) // 2]),
    "ValProbesOneMTwo": f2(SW["probes=1|honest|linear/gradual/audit"]["validity"]),
    "ValProbesOneMOne": f2(SW["probes=1|honest|linear/gradual/gross"]["validity"]),
    "ValClusteredMTwo": f2(SW["spread=clustered|honest|linear/gradual/audit"]["validity"]),
    "ValClusteredMZero": f2(SW["spread=clustered|honest|rank/cull/gross"]["validity"]),
    "ValRewardTenMZero": f2(SW["reward=10.0|honest|rank/cull/gross"]["validity"]),
    "ValKTwoMZero": f2(SW["k_tasks=2|honest|rank/cull/gross"]["validity"]),
}
with open(OUT / "numbers.tex", "a") as fh:
    fh.write("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in abl.items()))
print("ablation tables written; M1 beats M2 in:", m1better)
