"""Per-file multiset diff of numbers, protected LaTeX tokens and label words between two commits.
Usage: python3 token_diff.py OLD_SHA NEW_SHA  (run in the repo)."""
import collections, re, subprocess, sys
OLD, NEW = sys.argv[1], sys.argv[2]
DIR = "docs/paper/arxiv/sections/"
files = subprocess.run(["git", "diff", "--name-only", OLD, NEW, "--", DIR], capture_output=True, text=True, check=True).stdout.split()
def show(sha, f):
    r = subprocess.run(["git", "show", f"{sha}:{f}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""
def strip_comments(t):
    return "\n".join(re.sub(r"(?<!\\)%.*", "", l) for l in t.splitlines())
NUM = re.compile(r"(?<![A-Za-z])[-−+]?\d+(?:[.,]\d+)*")
PROT = re.compile(r"\\(?:label|ref|eqref|cref|Cref|cite[tp]?|commit|repopath|url|href|footnote)\*?(?:\[[^\]]*\])?\{[^}]*\}")
HEX = re.compile(r"\b[0-9a-f]{7,40}\b")
LABELS = ["confirmatory", "exploratory", "post hoc", "post-hoc", "pre-registered", "preregistered", "descriptive",
          "non-inferential", "not met", "met", "null", "significant", "n.s.", "replicat", "confirm", "establish",
          "demonstrat", "shows", "withdraw", "refut", "ruled out", "not found", "sensitivity", "push", "manipulation",
          "derived", "trend", "consistent with", "cannot", "does not", "causal"]
def labels(t):
    tl = t.lower()
    return collections.Counter({w: len(re.findall(r"\b" + re.escape(w), tl)) for w in LABELS})
def diff(a, b):
    ca, cb = collections.Counter(a), collections.Counter(b)
    return dict(cb - ca), dict(ca - cb)
total_bad = 0
for f in files:
    o, n = strip_comments(show(OLD, f)), strip_comments(show(NEW, f))
    o_nt = PROT.sub(" ", o); n_nt = PROT.sub(" ", n)
    print(f"=== {f}")
    for name, a, b in [("numbers", NUM.findall(o_nt), NUM.findall(n_nt)),
                       ("protected", PROT.findall(o), PROT.findall(n)),
                       ("hex", HEX.findall(o), HEX.findall(n))]:
        add, rem = diff(a, b)
        if add or rem:
            total_bad += 1
            print(f"  {name}: +{add}  -{rem}")
        else:
            print(f"  {name}: identical multiset ({len(a)})")
    lo, ln = labels(o), labels(n)
    ch = {w: (lo[w], ln[w]) for w in LABELS if lo[w] != ln[w]}
    print(f"  label-words changed (old,new): {ch}")
print("FILES WITH TOKEN DIFFS:", total_bad)
