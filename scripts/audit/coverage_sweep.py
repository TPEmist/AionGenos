"""Gate coverage sweep (Rule 3, exhaustive): mutate EVERY numeric literal in
shipped prose, one at a time, and record whether the birth-certificate gate
(all checks except REGENERATE, which reads no prose) rejects it.
Runs on a COPY of the audited tree; each mutation is reverted and md5-checked."""
import hashlib, importlib.util, re, sys, csv
from pathlib import Path
TREE = Path(sys.argv[1]); OUT = Path(sys.argv[2]); FILES = sys.argv[3:]
P = TREE / "docs/paper"
spec = importlib.util.spec_from_file_location("check", P / "birth_certificates/check.py")
ck = importlib.util.module_from_spec(spec); spec.loader.exec_module(ck)
DR = "/home/control/AionGenos"
def gate():
    return (ck.claims() + ck.residual_table() + ck.shas_resolve(DR) + ck.cost_claims()
            + ck.bar_claims(DR) + ck.a15_claims())
assert gate() == [], "gate not clean before sweep"
NUM = re.compile(r"(?<![A-Za-z0-9_.\\])\d+(?:\.\d+)?")
SKIP_CMD = re.compile(r"\\(cite[tp]?|ref|label|includegraphics|eqref|url|href|S|texttt|bibliography\w*|cline|cmidrule|resizebox|hspace|vspace|setcounter|small)\s*(\[[^\]]*\])?\{[^}]*$")
SKIP_AFTER = re.compile(r"^(\\linewidth|\\textwidth|pt\b|em\b|ex\b|\\columnwidth)")
md5 = lambda f: hashlib.md5(f.read_bytes()).hexdigest()
rows = []
for rel in FILES:
    f = P / rel; orig = f.read_text(); m0 = md5(f)
    lines = orig.split("\n"); end = len(lines)
    for i, ln in enumerate(lines):
        if re.match(r"\s*\\(bibliography|end\{document\})", ln): end = i; break
    for i in range(end):
        ln = lines[i]
        code = re.split(r"(?<!\\)%", ln, 1)[0]
        for m in NUM.finditer(code):
            pre = code[:m.start()]
            if SKIP_CMD.search(pre) or SKIP_AFTER.match(code[m.end():]): continue
            tok = m.group(0); d = tok[-1]; new = tok[:-1] + str((int(d) + 1) % 10)
            mut = lines[:]; mut[i] = code[:m.start()] + new + ln[m.end():]
            f.write_text("\n".join(mut))
            try: bad = gate()
            except Exception as e: bad = [f"EXC {type(e).__name__}: {e}"]
            f.write_text(orig)
            assert md5(f) == m0, f"RESTORE FAILED {rel}:{i+1}"
            ctx = " ".join(code[max(0, m.start()-40):m.end()+25].split())
            rows.append([rel, i + 1, tok, new, "CAUGHT" if bad else "MISSED", (bad[0] if bad else "")[:120], ctx])
with OUT.open("w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["file", "line", "token", "mutated", "result", "gate_msg", "context"]); w.writerows(rows)
n = len(rows); c = sum(r[4] == "CAUGHT" for r in rows)
print(f"{n} literals mutated, {c} caught, {n-c} missed -> {OUT}")
