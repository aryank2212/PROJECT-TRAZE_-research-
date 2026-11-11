"""Estimate characters-per-provider-token from live logs, to convert universal tokens into
approximate real tokens. The engine still meters by characters by default, so models with
different tokenisers pay the same for the same text; this only helps report real cost.

  PYTHONPATH=src python3 src/calibrate.py runs/live1.jsonl [more logs ...]
"""
import json
import sys

chars = toks = n = 0
for path in sys.argv[1:]:
    for line in open(path, encoding="utf-8"):
        e = json.loads(line)
        if e["kind"] == "task" and e.get("provider_tokens"):
            chars += e["reasoning_chars"]; toks += e["provider_tokens"]; n += 1
if not n:
    sys.exit("no provider token counts found")
print(f"calls={n} chars={chars} provider_tokens={toks} chars/token={chars / toks:.2f}")
print("rule 'chars/4' therefore reports %.2fx the provider's token count" % ((chars / 4) / toks))
