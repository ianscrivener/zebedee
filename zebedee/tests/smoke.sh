#!/usr/bin/env bash
# Zebedee smoke test: runs the full workflow in a throwaway copy of this repo.
# Usage: zebedee/tests/smoke.sh          (from the repo root)
# Uses $ZEBEDEE_CMD if set, else `python3 zebedee/zcli.py`. Needs git; just is not required.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
tar -C "$ROOT" --exclude=.venv --exclude=.records --exclude=.git --exclude=.zebedee-seed -cf - . | tar -C "$TMP" -xf - 2>/dev/null
cd "$TMP" && git init -q && git -c user.name=t -c user.email=t@t commit -q --allow-empty -m init
Z=${ZEBEDEE_CMD:-python3 zebedee/zcli.py}
pass=0; fail=0
ok()   { if "$@" >/dev/null 2>&1; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL (expected ok): $*"; fi; }
bad()  { if "$@" >/dev/null 2>&1; then fail=$((fail+1)); echo "FAIL (expected error): $*"; else pass=$((pass+1)); fi; }
z()    { $Z "$@"; }

ok  z setup
A=$(z init --harness test --family test --model test --session s1) || { echo "init failed"; exit 1; }
ok  z whoami --session s1
bad z item new --agent nope --title x --type bug --domains core
bad z item new --agent "$A" --title x --type epic --domains core
bad z item new --agent "$A" --title x --type bug --domains nope
bad z item new --agent "$A" --title x --type bug --domains core --stage 1          # needs intent
I=$(z item new --agent "$A" --title "spike one" --type enhancement --domains core --stage -1)
ok  z item doc "$I" spike --agent "$A"
bad z item stage "$I" --agent "$A" --to 2                                            # jump
ok  z item stage "$I" --agent "$A" --to 0
bad z item stage "$I" --agent "$A" --to 1                                            # needs decide
bad z item decide "$I" --agent "$A" --verdict park --reason r                        # needs revisit
ok  z item decide "$I" --agent "$A" --verdict commit --reason r
ok  z item stage "$I" --agent "$A" --to 2
bad z item stage "$I" --agent "$A" --to 1                                            # back needs reason
ok  z item stage "$I" --agent "$A" --to 1 --reason "spec was wrong"
B=$(z init --harness test --family test --model other)
bad z item claim "$I" --agent "$B"                                                   # live claim
ok  z item release "$I" --agent "$A"
ok  z item claim "$I" --agent "$B"
H=$(z item new --agent "$A" --title "historic" --type feature --domains core --stage 1 --intent i --as-of 2026-01-02T10:00)
[[ "$H" == 20260102-1000-* ]] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: as-of id ($H)"; }
bad z item stage "$H" --agent "$A" --to 2 --as-of 2025-12-01                          # before creation
bad z item stage "$H" --agent "$A" --to 2 --as-of 2099-01-01                          # future
ok  z item stage "$H" --agent "$A" --to 2 --as-of 2026-01-05
ok  z run record --agent "$A" --kind bench --name b --harness-version h --metrics '{"x":1}' --item "$I"
ok  z run record --agent "$A" --kind bench --name b --harness-version h --metrics '{"x":2}' --as-of 2026-01-03 --git-sha abc
bad z run record --agent "$A" --kind bench --name b --harness-version h --metrics 'notjson'
ok  z item list --all
ok  z run list
ok  z sessions
ok  z status --write
ok  z index
[ -d .records/.git ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: records git repo"; }
chk() { if eval "$1"; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: $2"; fi; }
chk '[ -f README-zebedee.md ]'                                   "manual not preserved"
chk '[ -f zebedee/LICENSE ] && [ ! -f LICENSE ]'                  "LICENSE not moved into zebedee/"
chk '[ -f zebedee/CHANGELOG.md ] && [ -f zebedee/RETROFIT_PROMPT.md ]' "seed files not moved"
# retrofit-like root: project's own README and LICENSE must be left alone
echo "# My project" > README.md; echo "project licence" > LICENSE; rm README-zebedee.md; $Z setup >/dev/null
chk '[ ! -f README-zebedee.md ] && grep -q "project licence" LICENSE' "touched a project's own files"
# maintainer checkout: marker present → nothing moves
printf '# Zebedee — an agent-native work ledger\n' > README.md; mv zebedee/CHANGELOG.md CHANGELOG.md; touch .zebedee-seed; $Z setup >/dev/null
chk '[ -f CHANGELOG.md ] && [ ! -f README-zebedee.md ]'          "moved files in seed checkout"

echo "smoke: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
