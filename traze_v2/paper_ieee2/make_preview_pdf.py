"""Render main.tex to an IEEE-style two-column PDF preview without a TeX install.

It converts only the LaTeX subset used by this paper (sections, lists, equations, theorem
blocks, tables fed by generated/*.tex, one pgfplots figure, cite/ref, simple math) to HTML and
prints it with headless Chromium. It is a PREVIEW: layout approximates IEEEtran, it is not
LaTeX output.

  python3 -I make_preview_pdf.py        (run from paper_ieee2/)
"""
import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEX = (HERE / "main.tex").read_text(encoding="utf-8")
BIB = (HERE / "references.bib").read_text(encoding="utf-8")
NUMS = (HERE / "generated" / "ieee_numbers.tex").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------------------
# helpers
def balanced(s, i):
    """s[i] == '{'. Return (content, index after closing brace)."""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced braces")


def sub_cmd(s, name, fn):
    out, i, pat = [], 0, "\\" + name
    while True:
        k = s.find(pat, i)
        if k < 0:
            out.append(s[i:])
            return "".join(out)
        end = k + len(pat)
        if end < len(s) and (s[end].isalpha()):
            out.append(s[i:end]); i = end; continue
        j = end
        while j < len(s) and s[j] == " ":
            j += 1
        if j >= len(s) or s[j] != "{":
            out.append(s[i:end]); i = end; continue
        arg, nxt = balanced(s, j)
        out.append(s[i:k]); out.append(fn(arg)); i = nxt


# ---------------------------------------------------------------------------------------
# numbers and bibliography
macros = {m: v for m, v in re.findall(r"\\newcommand\{\\(\w+)\}\{(.*?)\}\n", NUMS)}


def parse_bib(src):
    entries = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}\s*(?=@|\Z)", src, re.S):
        kind, key, body = m.group(1).lower(), m.group(2).strip(), m.group(3)
        fields, i = {}, 0
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            if fm.start() < i:
                continue
            j = fm.end()
            if body[j] == "{":
                val, i = balanced(body, j)
            elif body[j] == '"':
                k = body.index('"', j + 1); val, i = body[j + 1:k], k + 1
            else:
                k = re.search(r"[,\n]", body[j:]).start() + j; val, i = body[j:k], k
            fields[fm.group(1).lower()] = val.strip()
        entries[key] = (kind, fields)
    return entries


def clean(s):
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    s = s.replace("--", "–").replace("\\&", "&")
    s = re.sub(r"[{}]", "", s)
    return html.escape(s.strip())


def fmt_author(a):
    a = a.strip()
    if a.startswith("{"):
        return clean(a)
    if "," in a:
        last, first = [x.strip() for x in a.split(",", 1)]
    else:
        parts = a.split(); first, last = " ".join(parts[:-1]), parts[-1]
    ini = " ".join(p[0] + "." for p in re.split(r"[ ]+", first.replace("-", " ")) if p)
    return clean(f"{ini} {last}")


def fmt_ref(entry):
    kind, f = entry
    names = [fmt_author(a) for a in re.split(r"\s+and\s+", f.get("author", ""))]
    if len(names) > 6:
        who = names[0] + " <i>et al.</i>"
    elif len(names) > 2:
        who = ", ".join(names[:-1]) + ", and " + names[-1]
    else:
        who = " and ".join(names)
    title = clean(f.get("title", ""))
    yr = f.get("year", "")
    if kind == "inproceedings":
        return f'{who}, “{title},” in <i>{clean(f.get("booktitle", ""))}</i>, {yr}.'
    if kind == "misc":
        return f'{who}, “{title},” {clean(f.get("howpublished", ""))}. {clean(f.get("note", ""))}.'
    bits = f'<i>{clean(f.get("journal", ""))}</i>'
    if "volume" in f:
        bits += f', vol. {clean(f["volume"])}'
    if "number" in f:
        bits += f', no. {clean(f["number"])}'
    if "pages" in f:
        bits += f', pp. {clean(f["pages"])}'
    return f"{who}, “{title},” {bits}, {yr}."


BIBDB = parse_bib(re.sub(r"(?m)^%.*$", "", BIB))


# ---------------------------------------------------------------------------------------
# math
GREEK = {"theta": "θ", "delta": "δ", "gamma": "γ", "sigma": "σ", "tau": "τ", "epsilon": "ε"}


def math(m):
    s = m
    s = re.sub(r"\\tfrac\{([^}]*)\}\{([^}]*)\}", r"\1/\2", s)
    s = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"\1/\2", s)
    s = re.sub(r"\\sqrt\s*\{?([A-Za-z0-9]+)\}?", r"√\1", s)
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\sum_j", "Σ<sub>j</sub>", s)
    s = re.sub(r"\\in\b", "∈", s)
    s = s.replace("\\le", "≤").replace("\\ge", "≥").replace("\\ldots", "…").replace("\\dots", "…")
    s = s.replace("\\to", "→").replace("\\infty", "∞").replace("\\cdot", "·")
    for k, v in GREEK.items():
        s = s.replace("\\" + k, v)
    s = re.sub(r"\\mathbb\{R\}", "ℝ", s)
    s = s.replace("\\{", "\u27e6").replace("\\}", "\u27e7")
    s = re.sub(r"_\{([^}]*)\}", r"<sub>\1</sub>", s)
    s = re.sub(r"_([A-Za-z0-9])", r"<sub>\1</sub>", s)
    s = re.sub(r"\^\{([^}]*)\}", r"<sup>\1</sup>", s)
    s = re.sub(r"\^([A-Za-z0-9])", r"<sup>\1</sup>", s)
    s = s.replace("\\,", " ").replace("{", "").replace("}", "").replace("\\", "")
    s = s.replace("\u27e6", "{").replace("\u27e7", "}")
    s = s.replace("-", "−")
    return f'<span class="m">{s}</span>'


# ---------------------------------------------------------------------------------------
# figure (drawn from the coordinates that make_ieee.py wrote)
def coords(name):
    return [(float(a), float(b)) for a, b in re.findall(r"\(([\d.]+),([\d.]+)\)", macros[name])]


def panel(ox, title, xlab, series, xs, logx, legend):
    import math as mt
    W, H, L, B, T = 250, 120, 38, 28, 16
    px = lambda x: L + (mt.log(x) - mt.log(xs[0])) / (mt.log(xs[-1]) - mt.log(xs[0])) * (W - L - 8) if logx \
        else L + (x - xs[0]) / (xs[-1] - xs[0]) * (W - L - 8)
    py = lambda y: T + (1.05 - y) / 1.05 * (H - T - B)
    g = [f'<g transform="translate({ox},0)" font-size="8" font-family="Liberation Serif, serif">']
    g.append(f'<text x="{(L + W) / 2}" y="10" text-anchor="middle">{title}</text>')
    for yv in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
        g.append(f'<line x1="{L}" x2="{W - 8}" y1="{py(yv)}" y2="{py(yv)}" stroke="#bbb" stroke-width=".4"/>')
        g.append(f'<text x="{L - 4}" y="{py(yv) + 3}" text-anchor="end">{yv:g}</text>')
    for xv in xs:
        g.append(f'<line x1="{px(xv)}" x2="{px(xv)}" y1="{T}" y2="{H - B}" stroke="#bbb" stroke-width=".4"/>')
        g.append(f'<text x="{px(xv)}" y="{H - B + 10}" text-anchor="middle">{xv:g}</text>')
    g.append(f'<rect x="{L}" y="{T}" width="{W - 8 - L}" height="{H - B - T}" fill="none" stroke="#000" stroke-width=".6"/>')
    g.append(f'<text x="{(L + W) / 2}" y="{H - 6}" text-anchor="middle">{xlab}</text>')
    g.append(f'<text transform="translate(9,{(T + H - B) / 2}) rotate(-90)" text-anchor="middle">Rank match</text>')
    for k, pts in enumerate(series):
        d = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in pts)
        dash = ' stroke-dasharray="3,2"' if k else ""
        g.append(f'<polyline points="{d}" fill="none" stroke="#000" stroke-width="1.1"{dash}/>')
        for x, y in pts:
            shape = (f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="2"/>' if k == 0 else
                     f'<rect x="{px(x) - 2:.1f}" y="{py(y) - 2:.1f}" width="4" height="4"/>')
            g.append(shape)
    ly = py(0.12) if legend[0] else py(0.5)
    lx = L + 8 if legend[0] else W - 100
    for k, name in enumerate(legend[1]):
        yy = ly + k * 10
        dash = ' stroke-dasharray="3,2"' if k else ""
        g.append(f'<line x1="{lx}" x2="{lx + 14}" y1="{yy}" y2="{yy}" stroke="#000" stroke-width="1.1"{dash}/>')
        g.append(f'<text x="{lx + 18}" y="{yy + 3}">{name}</text>')
    g.append("</g>")
    return "".join(g)


def figure_svg():
    a = panel(0, "(a) Hardware speed", "Cost of one thinking step",
              [coords("CoordsHwTok"), coords("CoordsHwTime")], [1.5, 4, 8], False,
              (True, ["Count tokens", "Count time"]))
    b = panel(270, "(b) Number of audit tasks", "Audit tasks per round",
              [coords("CoordsProbeOne"), coords("CoordsProbeTwo")], [1, 3, 10], True,
              (False, ["Rank by earnings", "Rank by audit"]))
    return f'<svg viewBox="0 0 530 120" width="100%">{a}{b}</svg>'


# ---------------------------------------------------------------------------------------
# document conversion
def to_html():
    t = TEX
    t = re.sub(r"(?m)(?<!\\)%.*$", "", t)
    title = re.search(r"\\title\{(.*?)\}\n\n\\author", t, re.S).group(1)
    title = title.replace("\\\\", "<br>")
    author = re.search(r"\\IEEEauthorblockN\{(.*?)\}", t).group(1)
    k = t.index("\\IEEEauthorblockA") + len("\\IEEEauthorblockA")
    affil = balanced(t, k)[0].replace("\\\\", "<br>")
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", t, re.S).group(1)
    keywords = re.search(r"\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}", t, re.S).group(1)
    body = t.split("\\end{IEEEkeywords}")[1].split("\\bibliographystyle")[0]

    # numbering pass ----------------------------------------------------------------------
    roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
    labels, sec, sub, tab, fig, lem, prop = {}, 0, 0, 0, 0, 0, 0
    for m in re.finditer(r"\\(section\*?|subsection|begin\{table\}|begin\{figure\*\}|begin\{lemma\}|begin\{proposition\})(\{[^}]*\})?|\\label\{([^}]*)\}", body):
        cmd, lab = m.group(1), m.group(3)
        if cmd == "section":
            sec += 1; sub = 0; cur = roman[sec - 1]
        elif cmd == "subsection":
            sub += 1; cur = f"{roman[sec - 1]}-{chr(64 + sub)}"
        elif cmd == "begin{table}":
            tab += 1; cur = roman[tab - 1]
        elif cmd == "begin{figure*}":
            fig += 1; cur = str(fig)
        elif cmd == "begin{lemma}":
            lem += 1; cur = str(lem)
        elif cmd == "begin{proposition}":
            prop += 1; cur = str(prop)
        elif lab:
            labels[lab] = cur
    labels["eq:ledger"] = "1"

    # tables -------------------------------------------------------------------------------
    def table(m):
        blk = m.group(0)
        cap = re.search(r"\\caption\{(.*)\}\n\\label", blk, re.S).group(1)
        tcount = table.n = getattr(table, "n", 0) + 1
        k0 = blk.index("\\begin{tabular}") + len("\\begin{tabular}")
        _, k1 = balanced(blk, k0)
        tab_body = blk[k1:blk.index("\\end{tabular}")]
        tab_body = re.sub(r"\\input\{([^}]*)\}", lambda i: (HERE / (i.group(1) + ".tex")).read_text(encoding="utf-8"), tab_body)
        rows, header_done = [], False
        parts = re.split(r"\\toprule|\\midrule|\\bottomrule", tab_body)
        out = ['<table class="t">']
        for pi, part in enumerate(parts):
            if pi == 1:
                out.append('<tr class="rule"><td colspan="9"></td></tr>')
            for line in [x for x in part.replace("\\\\", "\n").split("\n") if x.strip()]:
                cells = []
                for c in re.split(r"&", line):
                    c = c.strip()
                    mc = re.match(r"\\multicolumn\{(\d+)\}\{[a-z]\}\{(.*)\}", c)
                    cells.append((int(mc.group(1)), mc.group(2)) if mc else (1, c))
                tag = "th" if pi == 1 else "td"
                out.append("<tr>" + "".join(f'<{tag} colspan="{n}">{inline(x)}</{tag}>' for n, x in cells) + "</tr>")
            if pi in (1, 2):
                out.append('<tr class="rule"><td colspan="9"></td></tr>')
        out.append("</table>")
        return (f'\n\n@@BLOCK<div class="tabwrap"><div class="cap">TABLE {roman[tcount - 1]}<br>{inline(cap).upper() if False else inline(cap)}</div>'
                + "".join(out) + "</div>@@\n\n")

    body = re.sub(r"\\begin\{table\}.*?\\end\{table\}", table, body, flags=re.S)
    cap_fig = re.search(r"\\begin\{figure\*\}.*?\\caption\{(.*?)\}\n\\label", body, re.S).group(1)
    body = re.sub(r"\\begin\{figure\*\}.*?\\end\{figure\*\}",
                  lambda m: f'\n\n@@BLOCK<div class="figwrap">{figure_svg()}<div class="figcap">Fig. 1. {inline(cap_fig)}</div></div>@@\n\n',
                  body, flags=re.S)

    # equations, lists, theorems ----------------------------------------------------------
    def eqn(m):
        c = re.sub(r"\\label\{[^}]*\}", "", m.group(1))
        c = " ".join(c.split()).rstrip(",").replace("\\text{", "\\text{")
        return f'\n\n@@BLOCK<div class="eq"><span>{math(c)}</span><span>(1)</span></div>@@\n\n'
    body = re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}", eqn, body, flags=re.S)

    def lst(m):
        kind = "ol" if m.group(1) == "enumerate" else "ul"
        items = [i.strip() for i in re.split(r"\\item\s*", m.group(2)) if i.strip()]
        return f"\n\n@@BLOCK<{kind}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{kind}>@@\n\n"
    body = re.sub(r"\\begin\{(itemize|enumerate)\}(.*?)\\end\{\1\}", lst, body, flags=re.S)

    counters = {"lemma": 0, "proposition": 0}

    def thm(m):
        kind = m.group(1); counters[kind] += 1
        txt = re.sub(r"\\label\{[^}]*\}", "", m.group(2))
        return f'\n\n<p class="thm"><b>{kind.capitalize()} {counters[kind]}.</b> <i>{inline(txt.strip())}</i></p>\n\n'
    body = re.sub(r"\\begin\{(lemma|proposition)\}(.*?)\\end\{\1\}", thm, body, flags=re.S)
    body = re.sub(r"\\begin\{proof\}(.*?)\\end\{proof\}",
                  lambda m: f'\n\n<p><i>Proof.</i> {inline(m.group(1).strip())} ∎</p>\n\n', body, flags=re.S)

    # sections -----------------------------------------------------------------------------
    sc = {"s": 0, "ss": 0}

    def sect(m):
        star, name = m.group(1), m.group(2)
        if star:
            return f"\n\n@@BLOCK<h2>{inline(name.upper())}</h2>@@\n\n"
        sc["s"] += 1; sc["ss"] = 0
        return f"\n\n@@BLOCK<h2>{roman[sc['s'] - 1]}. {inline(name.upper())}</h2>@@\n\n"
    body = re.sub(r"\\section(\*?)\{([^}]*)\}", sect, body)

    def subsect(m):
        sc["ss"] += 1
        return f"\n\n@@BLOCK<h3>{chr(64 + sc['ss'])}. {inline(m.group(1))}</h3>@@\n\n"
    body = re.sub(r"\\subsection\{([^}]*)\}", subsect, body)

    # paragraphs --------------------------------------------------------------------------
    chunks = re.split(r"\n\s*\n", body)
    out = []
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        if c.startswith("@@BLOCK"):
            out.append(c[len("@@BLOCK"):-2])
        elif c.startswith("<p class=\"thm\">") or c.startswith("<p>"):
            out.append(c)
        else:
            out.append(f"<p>{inline(c)}</p>")
    main_html = "\n".join(out)

    refs_html = "".join(f"<li>{fmt_ref(BIBDB[k])}</li>" for k in cite_order) if False else ""
    return title, author, affil, abstract, keywords, main_html


cite_order = []


def cite(keys):
    nums = []
    for k in [x.strip() for x in keys.split(",")]:
        if k not in cite_order:
            cite_order.append(k)
        nums.append(cite_order.index(k) + 1)
    return "[" + ", ".join(str(n) for n in nums) + "]"


LABELS = {}


def inline(s):
    s = re.sub(r"\\label\{[^}]*\}", "", s)
    s = re.sub(r"\\N([A-Za-z]+)\{\}", lambda m: macros["N" + m.group(1)].replace("\\%", "%"), s)
    s = sub_cmd(s, "textbf", lambda a: f"<b>{inline(a)}</b>")
    s = sub_cmd(s, "emph", lambda a: f"<i>{inline(a)}</i>")
    s = sub_cmd(s, "todo", lambda a: f'<span class="todo">[TODO: {inline(a)}]</span>')
    s = sub_cmd(s, "cite", cite)
    s = sub_cmd(s, "ref", lambda a: LABELS.get(a, "?"))
    s = sub_cmd(s, "texttt", lambda a: f"<code>{a}</code>")
    s = re.sub(r"\$([^$]+)\$", lambda m: math(m.group(1)), s)
    s = s.replace("``", "“").replace("''", "”").replace("---", "—").replace("--", "–")
    s = s.replace("~", "&nbsp;").replace("\\%", "%").replace("\\&", "&").replace("\\ ", " ")
    s = re.sub(r"\\(?:footnote)\{[^}]*\}", "", s)
    s = s.replace("{", "").replace("}", "")
    return s


CSS = """
@page { size: 8.5in 11in; margin: 0.75in 0.625in 1in 0.625in; }
html { font-family: 'Liberation Serif', 'Times New Roman', serif; font-size: 10pt; }
body { margin: 0; line-height: 12pt; }
.head { text-align: center; margin-bottom: 8pt; }
.head h1 { font-size: 24pt; line-height: 26pt; font-weight: normal; margin: 0 0 10pt 0; }
.head .au { font-size: 11pt; } .head .af { font-size: 9pt; font-style: italic; }
.cols { column-count: 2; column-gap: 0.25in; text-align: justify; hyphens: auto; }
p { margin: 0 0 0 0; text-indent: 0.17in; }
p.thm, p.noindent { text-indent: 0; margin: 3pt 0; }
.abs { font-weight: bold; font-size: 9pt; line-height: 11pt; margin-bottom: 6pt; text-indent: 0; }
.kw { font-weight: bold; font-style: italic; font-size: 9pt; line-height: 11pt; margin-bottom: 4pt; text-indent: 0; }
h2 { font-size: 10pt; font-weight: normal; text-align: center; margin: 10pt 0 4pt 0; break-after: avoid; }
h3 { font-size: 10pt; font-weight: normal; font-style: italic; margin: 6pt 0 2pt 0; break-after: avoid; }
ul, ol { margin: 3pt 0 3pt 0; padding-left: 0.22in; } li { text-indent: 0; }
.eq { display: flex; justify-content: space-between; margin: 4pt 0; font-style: italic; }
.m { font-style: italic; } sub, sup { font-size: 7pt; line-height: 0; }
.tabwrap { break-inside: avoid; margin: 5pt 0; font-size: 8pt; line-height: 10pt; }
.tabwrap .cap { text-align: center; text-indent: 0; margin-bottom: 3pt; }
table.t { border-collapse: collapse; margin: 0 auto; }
table.t td, table.t th { padding: 1pt 4pt; text-align: left; } table.t th { font-weight: bold; }
tr.rule td { border-top: 0.6pt solid #000; padding: 0; line-height: 0; }
.figwrap { column-span: all; margin: 8pt 0; break-inside: avoid; }
.figcap { font-size: 8pt; line-height: 10pt; text-align: justify; margin-top: 2pt; }
.refs { font-size: 8pt; line-height: 10pt; } .refs li { text-indent: 0; margin-bottom: 2pt; }
.todo { color: #c00; }
code { font-size: 9pt; }
"""


def main():
    # collect labels first (needs the same numbering as to_html)
    global LABELS
    t0 = re.sub(r"(?m)(?<!\\)%.*$", "", TEX)
    roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
    sec = sub = tab = fig = lem = prop = 0
    cur = ""
    for m in re.finditer(r"\\(section\*?|subsection|begin\{table\}|begin\{figure\*\}|begin\{lemma\}|begin\{proposition\})|\\label\{([^}]*)\}", t0.split("\\end{IEEEkeywords}")[1]):
        cmd, lab = m.group(1), m.group(2)
        if cmd == "section":
            sec += 1; sub = 0; cur = roman[sec - 1]
        elif cmd == "subsection":
            sub += 1; cur = f"{roman[sec - 1]}-{chr(64 + sub)}"
        elif cmd == "begin{table}":
            tab += 1; cur = roman[tab - 1]
        elif cmd == "begin{figure*}":
            fig += 1; cur = str(fig)
        elif cmd == "begin{lemma}":
            lem += 1; cur = str(lem)
        elif cmd == "begin{proposition}":
            prop += 1; cur = str(prop)
        elif lab:
            LABELS[lab] = cur
    LABELS["eq:ledger"] = "1"

    title, author, affil, abstract, keywords, main_html = to_html()
    refs_html = "".join(f"<li>[{i + 1}] {fmt_ref(BIBDB[k])}</li>" for i, k in enumerate(cite_order))
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Traze draft 2 (preview)</title>
<style>{CSS}</style></head><body>
<div class="head"><h1>{inline(title)}</h1><div class="au">{inline(author)}</div><div class="af">{inline(affil)}</div></div>
<div class="cols">
<p class="abs"><i>Abstract</i>—{inline(abstract.strip())}</p>
<p class="kw"><i>Index Terms</i>—{inline(keywords.strip())}</p>
{main_html}
<h2>REFERENCES</h2><ol class="refs" style="list-style:none;padding-left:0">{refs_html}</ol>
</div></body></html>"""
    out_html = HERE / "preview.html"
    out_html.write_text(doc, encoding="utf-8")
    pdf = HERE / "Traze_draft2_preview.pdf"
    with tempfile.TemporaryDirectory() as prof:
        cmd = ["chromium", "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={prof}",
               "--no-pdf-header-footer", f"--print-to-pdf={pdf}", out_html.as_uri()]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print("pdf written:", pdf.exists(), pdf, "| refs cited:", len(cite_order))
    if not pdf.exists():
        print(r.stderr[-800:], file=sys.stderr)


if __name__ == "__main__":
    main()
