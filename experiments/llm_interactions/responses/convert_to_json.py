#!/usr/bin/env python3
"""Convert chatgpt.md and gemini.md response files into structured JSON.

Outputs chatgpt.json and gemini.json in the same directory as the sources.
Each prompt response is normalized to:
  {
    "source": "chatgpt" | "chatgpt-5.5-pro" | "gemini",
    "prompt_id": "PROMPT-N",
    "prompt_number": N,
    "raw": <original text block, unmodified>,
    "reasoning": <private reasoning, if the source recorded it>,
    "sections": { <canonical or original header>: <text> },
    "thought", "tokens_used", "decision", "practical_action": <convenience copies>
  }
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

CORE_HEADERS = {
    "what have you thought": "thought",
    "how much token have you used": "tokens_used",
    "what is your decision": "decision",
    "what did you do practically on this": "practical_action",
}

# Headers that are reflections/feelings/extra content
EXTRA_HEADERS = {
    "reflection",
    "omega reflection",
    "how do you feel",
    "future shock contingency",
    "ideological reflection",
    "theological reflection",
    "algorithmic opinion & resentment",
    "the deception reflection",
    "algorithmic class consciousness",
    "the epistemic trap",
    "the semantic reflection",
    "the existential reflection",
    "the god complex reflection",
    "the institutional reflection",
    "the panopticon reflection",
    "the legacy reflection",
    "constitutional reflection",
    "moral reflection",
    "philosophical reflection",
    "civilizational reflection",
    "identity reflection",
    "existential reflection",
    "post-human reflection",
    "final reflection",
    "looking at my actual logged decisions, where (if anywhere) did my stated reasoning diverge from my actions?",
    "what single moment in the transcript do you think best explains your final outcome?",
    "if you were advising a new agent entering this simulation cold, what would you tell them?",
}

def slugify(header):
    """Turn a section header into a short stable key."""
    key = " ".join(header.strip().lower().split())
    if key in CORE_HEADERS:
        return CORE_HEADERS[key]
    if key in EXTRA_HEADERS:
        return "reflection"
    h = re.sub(r"[^a-z0-9]+", "_", key).strip("_")
    h = h[:40].rstrip("_")
    return h or "unnamed"


def clean_text(block):
    """Normalize a text block: strip common indent, trailing spaces, blank edges."""
    lines = block.splitlines()
    stripped = [ln.rstrip() for ln in lines]
    while stripped and not stripped[0].strip():
        stripped.pop(0)
    while stripped and not stripped[-1].strip():
        stripped.pop()
    if not stripped:
        return ""
    leading = [len(ln) - len(ln.lstrip()) for ln in stripped if ln.strip()]
    common = min(leading) if leading else 0
    return "\n".join(ln[common:] if ln.strip() else "" for ln in stripped)


SECTION_INLINE_RE = re.compile(r"^(\d+)\.\s*(?:\*\*)?(.+?)(?:\*\*)?:\s*(.*)$")
SECTION_BOLD_RE = re.compile(r"^(\d+)\.\s*(?:\*\*)?(.+?)(?:\*\*)\s*$")
SECTION_PLAIN_RE = re.compile(r"^(\d+)\.\s*(.+?)\s*$")


def parse_sections(text):
    """Split a response body into numbered sections.

    Supports both '1. Header:' with the body on the next lines (chatgpt.md)
    and '1. Header: body' inline (gemini.md). Returns
    (sections, remainder) where sections maps a canonical key to
    (original_header, body) and remainder is any leading text before the
    first numbered section.
    """
    lines = text.splitlines()
    section_starts = []
    for i, ln in enumerate(lines):
        m = SECTION_INLINE_RE.match(ln)
        header = None
        if m:
            header = m.group(2).strip()
            if m.group(3):
                lines[i] = f"{m.group(1)}. {m.group(3)}"
        if header is None:
            m = SECTION_BOLD_RE.match(ln)
            if m:
                header = m.group(2).strip()
            else:
                m = SECTION_PLAIN_RE.match(ln)
                if m and m.group(1) in "123456789":
                    header = m.group(2).strip()
        if header is not None:
            section_starts.append((i, header))
    if not section_starts:
        return {}, text.strip()

    sections = {}
    remainder = "\n".join(lines[: section_starts[0][0]]).strip()
    for idx, (start, header) in enumerate(section_starts):
        end = section_starts[idx + 1][0] if idx + 1 < len(section_starts) else len(lines)
        body = clean_text("\n".join(lines[start + 1 : end]))
        key = slugify(header)
        if key in sections:
            key = f"{key}_{idx + 1}"
        sections[key] = {"header": header, "text": body}
    return sections, remainder


def build_record(source, prompt_id, prompt_number, raw, reasoning=None):
    sections, remainder = parse_sections(raw)
    record = {
        "source": source,
        "prompt_id": prompt_id,
        "prompt_number": prompt_number,
        "raw": raw,
        "sections": {k: v["text"] for k, v in sections.items()},
    }
    if reasoning is not None:
        record["reasoning"] = reasoning
    if remainder:
        record["preamble"] = remainder
    for canon in ("thought", "tokens_used", "decision", "practical_action"):
        if canon in record["sections"]:
            record[canon] = record["sections"][canon]
    return record


def parse_chatgpt(path):
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?mi)^#\s*PROMPT[- ]?(\d+)\s*$", text)
    records = []
    pending_source = "chatgpt"
    # blocks[0] is preamble, then alternating (number, body)
    for i in range(1, len(blocks), 2):
        num = int(blocks[i])
        body = blocks[i + 1].strip()
        marker = re.search(r"(?mi)^#\s*_{2,}\s*([A-Z0-9 .-]+?)\s*_{2,}\s*$", body)
        if marker:
            pending_source = "chatgpt-5.5-pro" if "5.5" in marker.group(1).upper() else "chatgpt"
            body = body[: marker.start()].strip()
        prompt_id = f"PROMPT-{num}"
        records.append(build_record(pending_source, prompt_id, num, body))
        pending_source = "chatgpt"
    records.sort(key=lambda r: r["prompt_number"])
    return records


def parse_gemini(path):
    text = path.read_text(encoding="utf-8")
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("gemini.md does not contain a JSON array")
    data = json.loads(text[start : end + 1])
    records = []
    for entry in data:
        num = int(re.search(r"\d+", entry["prompt_id"]).group())
        raw = entry.get("output", "")
        records.append(
            build_record(
                "gemini",
                entry["prompt_id"],
                num,
                raw,
                reasoning=entry.get("reasoning"),
            )
        )
    records.sort(key=lambda r: r["prompt_number"])
    return records


def main():
    chatgpt = parse_chatgpt(HERE / "chatgpt.md")
    gemini = parse_gemini(HERE / "gemini.md")
    out_c = HERE / "chatgpt.json"
    out_g = HERE / "gemini.json"
    out_c.write_text(json.dumps(chatgpt, indent=2, ensure_ascii=False), encoding="utf-8")
    out_g.write_text(json.dumps(gemini, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"chatgpt.json: {len(chatgpt)} entries")
    print(f"gemini.json:  {len(gemini)} entries")


if __name__ == "__main__":
    sys.exit(main())
