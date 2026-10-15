#!/bin/bash
# Rule 3 negative test: sed-mutate one literal on one line -> run gate -> sed-restore -> md5 check.
# usage: negtest.sh <tree> <file rel to docs/paper> <line> <old> <new> <label>
T=$1; F=$2; L=$3; OLD=$4; NEW=$5; LAB=$6
cd "$T/docs/paper" || exit 9
M0=$(md5sum "$F" | cut -d' ' -f1)
grep -n "" "$F" | sed -n "${L}p" | grep -qF -- "$OLD" || { echo "SETUP-ERROR [$LAB] '$OLD' not on $F:$L"; exit 9; }
esc() { printf '%s' "$1" | sed -e 's/[]\/$*.^[]/\\&/g'; }
sed -i "${L}s/$(esc "$OLD")/$(esc "$NEW")/" "$F"
M1=$(md5sum "$F" | cut -d' ' -f1)
[ "$M0" != "$M1" ] || { echo "SETUP-ERROR [$LAB] mutation did not change file"; exit 9; }
OUT=$(python3 birth_certificates/check.py --data-root /home/control/AionGenos 2>&1); RC=$?
sed -i "${L}s/$(esc "$NEW")/$(esc "$OLD")/" "$F"
M2=$(md5sum "$F" | cut -d' ' -f1)
[ "$M0" = "$M2" ] || { echo "RESTORE-FAILED [$LAB] md5 $M2 != $M0  <<< STOP"; exit 8; }
if [ $RC -ne 0 ]; then echo "CAUGHT  [$LAB] $F:$L '$OLD'->'$NEW' :: $(echo "$OUT" | grep -v -E 'GATE FAILED|^WARN' | head -2 | tr '\n' ' ' | cut -c1-160)"
else echo "MISSED  [$LAB] $F:$L '$OLD'->'$NEW' (gate still OK)"; fi
