#!/usr/bin/env bash
# Publish a daily AI news HTML report to the GitHub Pages site.
# Usage:
#   /workspace/ai-news-site/publish.sh /workspace/reports/ai-news-YYYY-MM-DD.html
#
# Copies the file into reports/, rebuilds index.html (latest report) and
# archive.html, then commits and pushes to origin/main. Safe to re-run:
# identical content produces no commit.

set -euo pipefail

usage() {
  echo "Usage: $0 <path-to-report.html>" >&2
  echo "Example: $0 /workspace/reports/ai-news-2026-11-22.html" >&2
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]]; then
  usage
fi

SITE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORTS_DIR="${SITE_ROOT}/reports"
SRC="$1"

if [[ ! -f "$SRC" ]]; then
  echo "error: file not found: $SRC" >&2
  exit 1
fi

SRC="$(cd "$(dirname "$SRC")" && pwd)/$(basename "$SRC")"
BASENAME="$(basename "$SRC")"

if [[ ! "$BASENAME" =~ ^ai-news-[0-9]{4}-[0-9]{2}-[0-9]{2}\.html$ ]]; then
  echo "error: expected a filename like ai-news-YYYY-MM-DD.html, got: $BASENAME" >&2
  exit 1
fi

DATE="${BASENAME#ai-news-}"
DATE="${DATE%.html}"

mkdir -p "$REPORTS_DIR"
cp "$SRC" "${REPORTS_DIR}/${BASENAME}"

python3 "${SITE_ROOT}/rebuild_site.py"

cd "$SITE_ROOT"

if [[ ! -d .git ]]; then
  echo "warning: $SITE_ROOT is not a git repository; files were updated, skipping commit/push."
  exit 0
fi

if [[ -z "$(git config --local user.name || true)" ]]; then
  git config --local user.name "Hossam Mostafa"
fi
if [[ -z "$(git config --local user.email || true)" ]]; then
  git config --local user.email "25941489+SEREPie@users.noreply.github.com"
fi

git add -- "reports/${BASENAME}" index.html archive.html .nojekyll rebuild_site.py publish.sh

if git diff --cached --quiet; then
  echo "No changes to publish for ${BASENAME}."
  exit 0
fi

git commit -m "Publish AI news report ${DATE}"

if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  git push
elif git remote get-url origin >/dev/null 2>&1; then
  branch="$(git rev-parse --abbrev-ref HEAD)"
  git push -u origin "$branch"
else
  echo "warning: no git remote configured; commit created but not pushed."
  exit 0
fi

echo "Published ${BASENAME}."
