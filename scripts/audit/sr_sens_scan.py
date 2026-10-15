"""List every sentence that states an SR count/percentage for a D11/A15 arm and
has no sensitivity value in the same sentence (lock: pin 8, 'beside every SR')."""
import re, sys
from pathlib import Path
SR = re.compile(r"(\b\d{1,3}/100\b|\b\d{1,3}\s+of\s+100\b|\b\d{1,2}(?:--\d{1,2})?\\?%|\bto \d{2}, \d{2} and \d{2}\b|\bfrom \d{2}, \d{2} and \d{2}\b|\(\d{2} vs \d{2}|\d{2} vs \d{2} of 100)")
SENS = re.compile(r"sensitiv|sens\.|\(\d{1,2}\)|in parentheses", re.I)
CTX = re.compile(r"retriev|adapter|A\\?_|B\\?_main|C\\?_retrieval|D\\?_gist|buffer|teacher|SR|success", re.I)
for tree in sys.argv[1:]:
    for f in sorted(Path(tree, "docs/paper").glob("arxiv/sections/*.tex")) + [Path(tree, "docs/paper/bar/main.tex")]:
        txt = f.read_text()
        for m in re.finditer(r"[^.;]*?(?:\.(?=\s)|;|$)", txt, re.S):
            s = m.group(0)
            if SR.search(s) and CTX.search(s) and not SENS.search(s) and "%" not in s.split("\n")[0][:1]:
                line = txt[:m.start()].count("\n") + 1 + (len(s) - len(s.lstrip("\n")) and 0)
                flat = " ".join(s.split())
                if flat.startswith("%"): continue
                print(f"{f.relative_to(tree)}:{line}: {flat[:230]}")
