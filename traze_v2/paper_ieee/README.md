# IEEE two-column paper (first draft)

- `main.tex`: the paper (IEEEtran, conference mode, two columns), plain language, target at most 5 pages.
- `references.bib`: 15 cited papers (IEEEtran bibliography style).
- `make_ieee.py`: builds every table, plotted point and number from `../results.json`, `../results_ablation.json` and `../runs/*.jsonl` into `generated/`.

Build (needs IEEEtran and pgfplots; both are on Overleaf):

    python3 -I make_ieee.py
    pdflatex main && bibtex main && pdflatex main && pdflatex main

Not compiled where it was written (no TeX install), so the page count is an estimate (about 4 pages). Check the compiled PDF.
