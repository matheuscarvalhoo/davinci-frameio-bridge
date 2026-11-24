#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scan-secrets.sh — pre-commit secret sweeper
#
# Scans the repo (tracked files only) for anything that smells like a real
# credential. Exit code != 0 blocks CI / your pre-commit hook.
#
# Patterns covered:
#   * Adobe IMS client secrets (p8e-*, s8e-*, p8g-*, ims-na1 prefixed)
#   * Hex client IDs of Adobe-typical length (32 hex chars)
#   * OAuth bearer / refresh tokens (eyJ... JWTs, long base64url blobs)
#   * AWS access keys (AKIA*, ASIA*) — cover for S3 upload URLs leaking
#   * Generic "client_secret" / "refresh_token" assignments with real values
#   * .env style lines with secret-ish values
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/..")"

RED=$'\e[31m'; YELLOW=$'\e[33m'; GREEN=$'\e[32m'; NC=$'\e[0m'
hits=0

# Files to scan — tracked by git, excluding common binary/vendor stuff
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  FILES=(); while IFS= read -r l; do FILES+=("$l"); done < <(git ls-files | grep -Ev '\.(png|jpg|jpeg|gif|mp4|mov|wav|pdf|zip|tar|gz)$|^LICENSE$|scan-secrets\.sh$|\.gitignore$|SECURITY\.md$|config\.example\.json$')
else
  mapfile -t FILES < <(find . -type f \
      ! -path './.git/*' ! -path './.venv/*' ! -path './venv/*' \
      ! -path './__pycache__/*' \
      ! -name '*.png' ! -name '*.mp4' ! -name '*.mov' ! -name '*.pdf')
fi

check() {
  local label="$1"; shift
  local pattern="$1"; shift
  local out
  out=$(grep -nIE "$pattern" "${FILES[@]}" 2>/dev/null || true)
  if [ -n "$out" ]; then
    echo "${RED}[FAIL] ${label}${NC}"
    echo "$out"
    echo
    hits=$((hits + 1))
  fi
}

echo ">> scanning $(echo "${FILES[@]}" | wc -w) files"
echo

# 1. Adobe IMS client secrets
check "Adobe client_secret (p8e-/s8e-/p8g-)" '(p8e|s8e|p8g)-[A-Za-z0-9_-]{32,}'

# 2. 32-char hex client IDs assigned to a variable (not comments)
check "Hex client_id (32 hex chars)" '"client_id"[[:space:]]*:[[:space:]]*"[a-f0-9]{32}"'

# 3. JWT-ish bearer / refresh tokens
check "JWT-like token" 'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'

# 4. AWS keys
check "AWS Access Key ID" '(AKIA|ASIA)[0-9A-Z]{16}'

# 5. Generic secret-ish assignments with non-placeholder values
check "client_secret with real value" '"client_secret"[[:space:]]*:[[:space:]]*"[A-Za-z0-9_\-]{20,}"'
check "refresh_token with real value" '"refresh_token"[[:space:]]*:[[:space:]]*"[A-Za-z0-9_.\-]{20,}"'
check "access_token with real value"  '"access_token"[[:space:]]*:[[:space:]]*"[A-Za-z0-9_.\-]{20,}"'

# 6. .env lines
check ".env style secret"   '^(SECRET|TOKEN|KEY|PASS|PASSWORD|PWD|API_KEY)[A-Z_]*=[A-Za-z0-9_\-]{12,}'

# 7. Signed S3 upload URLs (look for X-Amz-Signature=...)
check "Signed S3 URL in source" 'X-Amz-Signature=[A-Fa-f0-9]{20,}'

# 8. Email addresses that could identify the author beyond the LICENSE
#    (we allow public ones in SECURITY.md etc)
check "Raw email address in source" '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' \
  2>/dev/null || true

if [ "$hits" -eq 0 ]; then
  echo "${GREEN}OK — no credential-shaped strings found.${NC}"
  exit 0
else
  echo "${RED}$hits pattern(s) matched — resolve before committing.${NC}"
  echo "${YELLOW}If a match is a false positive, add a specific allowlist in this script.${NC}"
  exit 1
fi
