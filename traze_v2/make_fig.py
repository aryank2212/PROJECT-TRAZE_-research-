import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

r = json.loads(Path(__file__).with_name("results.json").read_text())
m, h = r["mechanisms"], r["hardware"]
fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))

names = ["M0_reference", "M0t_tokens", "M1_linear", "M2_audit"]
lab = ["M0 ref", "M0 tokens", "M1 linear", "M2 audit"]
for off, pol, c in ((-0.2, "honest", "#4477aa"), (0.2, "strategic", "#cc6677")):
    vals = [m[f"strong|{pol}|hw=0|{n}"]["validity"] for n in names]
    ax[0].bar([i + off for i in range(4)], vals, 0.4, label=pol, color=c)
ax[0].set_xticks(range(4)); ax[0].set_xticklabels(lab, fontsize=8)
ax[0].set_ylabel("rank validity (Spearman, capability vs survival)")
ax[0].set_title("(a) Strong colony: does survival track capability?", fontsize=9)
ax[0].legend(fontsize=8)

costs = [1.5, 4.0, 8.0]
for mk, c, ls in (("M1_linear", "#4477aa", "-"), ("M1_time", "#cc6677", "--")):
    ax[1].plot(costs, [h[f"cost={x}|{mk}|hw=1"]["validity"] for x in costs], ls, marker="o", color=c, label=mk + " (mixed hardware)")
ax[1].set_xlabel("token cost per reasoning-depth unit"); ax[1].set_ylabel("rank validity")
ax[1].set_title("(b) Time metering breaks validity as tokens get costly", fontsize=9)
ax[1].legend(fontsize=8)

ext = [m[f"weak|honest|hw=0|{n}"]["extinct"] for n in names]
ax[2].bar(range(4), ext, color=["#cc6677", "#cc6677", "#4477aa", "#4477aa"])
ax[2].set_xticks(range(4)); ax[2].set_xticklabels(lab, fontsize=8)
ax[2].set_ylabel("share of colonies that go extinct")
ax[2].set_title("(c) Weak colony: extinction rate", fontsize=9)
plt.tight_layout()
plt.savefig(Path(__file__).with_name("fig_v2_results.png"), dpi=150)
