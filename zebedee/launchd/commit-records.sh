#!/bin/sh
# Commit the records store. Run by launchd; agents never run git in .records/.
# Usage: commit-records.sh /absolute/path/to/project/.records
set -eu
RECORDS="${1:?usage: commit-records.sh /path/to/.records}"
cd "$RECORDS"
[ -d .git ] || exit 0
git add -A
if ! git diff --cached --quiet; then
  git -c user.name="zebedee" -c user.email="zebedee@localhost" \
    commit -q -m "records: auto-commit $(date '+%Y-%m-%d %H:%M')"
fi
