#!/bin/bash
# PREPUB F1 for the TMLR (double-blind) build: six grep categories over the PDF
# text + PDF metadata, plus the tmlr.sty md5 against the official style file.
# Exit 0 only when every category has zero hits AND the style md5 matches.
#   usage: tmlr_anon_check.sh <main.pdf> [<tmlr.sty used by the build>]
# Category 5 resolves 7-hex tokens against the PUBLIC repo checkout (any commit
# reachable from origin/master identifies the named repository).
set -u
PDF=$1; STY=${2:-}
REPO=/home/control/AionGenos
OFFICIAL_TMLR_STY_MD5=e302463e460a0173d5bee936bc95a625   # JmlrOrg/tmlr-style-file main.zip, fetched 2026-10-16T00:08Z
TXT=$(mktemp); pdftotext "$PDF" "$TXT"
fail=0
cat_check() {  # label, extended regex
  local n; n=$(grep -c -i -E "$2" "$TXT")
  printf '%-34s %3d hit(s)\n' "$1" "$n"
  [ "$n" -gt 0 ] && { grep -n -i -o -E ".{0,30}($2).{0,30}" "$TXT" | head -5 | sed 's/^/      /'; fail=1; }
}
cat_check "1 author name"            "Cheng-?Yin|Chengyin|C\.-?Y\. Tu|\bTu,? C"
cat_check "2 affiliation / company"  "Nikon|NRCA|Research Corporation of America"
cat_check "3 e-mail"                 "[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}"
cat_check "4 repo / account / hosting" "TPEmist|AionGenos|github\.com|huggingface\.co|zenodo|anonymous\.4open"
# 5: public-repo commit SHAs + package code paths
n5=0; hits=""
for t in $(grep -o -E '\b[0-9a-f]{7,40}\b' "$TXT" | grep -E '[a-f]' | grep -E '[0-9]' | sort -u); do
  if git -C "$REPO" merge-base --is-ancestor "$t" origin/master 2>/dev/null; then n5=$((n5+1)); hits="$hits $t"; fi
done
np=$(grep -c -E "aiongenos/" "$TXT"); n5=$((n5+np))
printf '%-34s %3d hit(s)\n' "5 public commit SHA / code path" "$n5"
[ "$n5" -gt 0 ] && { echo "      SHAs on public origin:${hits:- none}; 'aiongenos/' paths: $np"; fail=1; }
cat_check "6 ack / funding / self-cite / local" "Acknowledg|funded by|grant (no|number)|our (previous|prior|earlier) (work|paper)|/home/|10\.80\.|exx@"
# PDF metadata
meta=$(pdfinfo "$PDF" | grep -E "^(Title|Author|Subject|Keywords|Creator):" | grep -i -E "cheng|tu\b|nikon|tpemist|aiongenos|@")
printf '%-34s %3d hit(s)\n' "metadata (Title/Author/…)" "$( [ -n "$meta" ] && echo 1 || echo 0)"
[ -n "$meta" ] && { echo "      $meta"; fail=1; }
if [ -n "$STY" ]; then
  m=$(md5sum "$STY" | cut -d' ' -f1)
  if [ "$m" = "$OFFICIAL_TMLR_STY_MD5" ]; then echo "tmlr.sty md5 $m = official"; else echo "tmlr.sty md5 $m != official $OFFICIAL_TMLR_STY_MD5"; fail=1; fi
else
  echo "tmlr.sty: not given (E5-TMLR not checked)"; fail=1
fi
rm -f "$TXT"
[ $fail -eq 0 ] && echo "TMLR ANON CHECK: PASS" || echo "TMLR ANON CHECK: FAIL"
exit $fail
