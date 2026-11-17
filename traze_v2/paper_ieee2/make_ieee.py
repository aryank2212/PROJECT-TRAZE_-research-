"""Build every table, figure data point and number for the IEEE paper from the result files.

  python3 -I paper_ieee2/make_ieee.py        (run from traze_v2/)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper_ieee2" / "generated"
OUT.mkdir(exist_ok=True)
R = json.loads((ROOT / "results.json").read_text())
A = json.loads((ROOT / "results_ablation.json").read_text())
F, SW, LK = A["factorial"], A["sweeps"], A["lookahead"]
f2 = lambda x: f"{x:.2f}"
pct = lambda x: f"{100 * x:.0f}\\%"

# ---- Table I: which rule matters (strong colony) ---------------------------------------
rows = [
    ("rank tax", "one-shot", "gross", "rank/cull/gross"),
    ("rank tax", "gradual", "gross", "rank/gradual/gross"),
    ("rank tax", "gradual", "audit", "rank/gradual/audit"),
    ("linear tax", "one-shot", "gross", "linear/cull/gross"),
    ("linear tax", "gradual", "gross", "linear/gradual/gross"),
    ("linear tax", "gradual", "audit", "linear/gradual/audit"),
    ("no tax", "gradual", "audit", "none/gradual/audit"),
]
lines = []
for a, b, c, key in rows:
    h, s = F[f"strong|honest|{key}"], F[f"strong|strategic|{key}"]
    lines.append(f"{a} & {b} & {c} & {f2(h['validity'])} & {f2(s['validity'])} \\\\")
lines.append("\\midrule")
h, s = F["strong|honest|baseline"], F["strong|strategic|baseline"]
lines.append(f"\\multicolumn{{3}}{{l}}{{no economy at all (bare tournament)}} & {f2(h['validity'])} & {f2(s['validity'])} \\\\")
(OUT / "tab_rules.tex").write_text("\n".join(lines) + "\n")

# ---- Table II: first tests with a real model ---------------------------------------------
live = []
for ln in (ROOT / "paper" / "generated" / "tab_live.tex").read_text().splitlines():
    p = [x.strip().rstrip("\\").strip() for x in ln.split("&")]
    if len(p) == 9:
        live.append(p)   # run, rounds, price, correct, cut, probes, plan share, plan cut, chars/token
lines = [f"{p[0]} & {p[1]} & {p[3]} & {p[4]} & {p[6]} & {p[7]} & {p[8]} \\\\" for p in live]
(OUT / "tab_live.tex").write_text("\n".join(lines) + "\n")

# ---- Figure data (pgfplots coordinates) --------------------------------------------------
H = R["hardware"]
costs = (1.5, 4.0, 8.0)
coords = lambda xs, ys: " ".join(f"({x},{y:.3f})" for x, y in zip(xs, ys))
fig = {
    "HwTok": coords(costs, [H[f"cost={c}|M1_linear|hw=1"]["validity"] for c in costs]),
    "HwTime": coords(costs, [H[f"cost={c}|M1_time|hw=1"]["validity"] for c in costs]),
}
probes = (1, 3, 10)
fig["ProbeOne"] = coords(probes, [SW[f"probes={p}|honest|linear/gradual/gross"]["validity"] for p in probes])
fig["ProbeTwo"] = coords(probes, [SW[f"probes={p}|honest|linear/gradual/audit"]["validity"] for p in probes])
text = "".join(f"\\newcommand{{\\Coords{k}}}{{{v}}}\n" for k, v in fig.items())

# ---- Scalars used in the text -----------------------------------------------------------
D = R["depth"]
M = R["mechanisms"]
g = lambda k: F[k]
nums = {
    "VMzeroH": f2(g("strong|honest|rank/cull/gross")["validity"]),
    "VMzeroS": f2(g("strong|strategic|rank/cull/gross")["validity"]),
    "CMzeroH": f2(g("strong|honest|rank/cull/gross")["cindex"]),
    "CMtwoH": f2(g("strong|honest|linear/gradual/audit")["cindex"]),
    "VLinCull": f2(g("strong|honest|linear/cull/gross")["validity"]),
    "VLinGrad": f2(g("strong|honest|linear/gradual/gross")["validity"]),
    "VLinGradAudit": f2(g("strong|honest|linear/gradual/audit")["validity"]),
    "VBare": f2(g("strong|honest|baseline")["validity"]),
    "VRankGradGrossH": f2(g("strong|honest|rank/gradual/gross")["validity"]),
    "VRankGradGrossS": f2(g("strong|strategic|rank/gradual/gross")["validity"]),
    "VRankGradAuditH": f2(g("strong|honest|rank/gradual/audit")["validity"]),
    "VWeakInverted": f2(g("weak|honest|rank/gradual/audit")["validity"]),
    "ExtWeakInverted": pct(g("weak|honest|rank/gradual/audit")["extinct"]),
    "ExtWeakMzero": pct(M["weak|honest|hw=0|M0_reference"]["extinct"]),
    "BestDeadWeakMzero": pct(M["weak|honest|hw=0|M0_reference"]["best_dead_early"]),
    "HwTokFour": f2(H["cost=4.0|M1_linear|hw=1"]["validity"]),
    "HwTimeFour": f2(H["cost=4.0|M1_time|hw=1"]["validity"]),
    "HwTokEight": f2(H["cost=8.0|M1_linear|hw=1"]["validity"]),
    "HwTimeEight": f2(H["cost=8.0|M1_time|hw=1"]["validity"]),
    "MidEffMyopic": f2(LK["strong|myopic|rank/cull/gross"]["mid_effort"]),
    "MidEffLook": f2(LK["strong|lookahead|rank/cull/gross"]["mid_effort"]),
    "ProbesOneOne": f2(SW["probes=1|honest|linear/gradual/gross"]["validity"]),
    "ProbesOneTwo": f2(SW["probes=1|honest|linear/gradual/audit"]["validity"]),
    "LowIncomeMzero": f2(SW["reward=10.0|honest|rank/cull/gross"]["validity"]),
    "DepthAdaptiveEight": f"{D['cost=8.0|M1_linear']['adaptive_surv']:.0f}",
    "DepthFixedEight": f"{D['cost=8.0|M1_linear']['fixed_surv']:.0f}",
}
gaps, flips = [], 0
for key in SW:
    if key.endswith("|rank/cull/gross"):
        base = key[: -len("rank/cull/gross")]
        gap = SW[base + "linear/gradual/audit"]["validity"] - SW[key]["validity"]
        gaps.append(gap); flips += gap < 0
nums["SweepCount"] = str(len(gaps)); nums["SweepBelow"] = str(flips)
nums["SweepMedian"] = f2(sorted(gaps)[len(gaps) // 2]); nums["SweepMin"] = f2(min(gaps))
text += "".join(f"\\newcommand{{\\N{k}}}{{{v}}}\n" for k, v in nums.items())
(OUT / "ieee_numbers.tex").write_text(text)
print("ok:", sorted(p.name for p in OUT.iterdir()))
