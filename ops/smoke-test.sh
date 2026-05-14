#!/usr/bin/env bash
# End-to-end smoke test: validates the running stack returns expected responses.
# Run after `docker compose up`.
#
#   bash ops/smoke-test.sh
#
# Exits 0 on success, non-zero on failure.
set -e

API="${API:-http://localhost:8000/api/v1}"
WEB="${WEB:-http://localhost:3000}"
EMAIL="${EMAIL:-admin@india-trade.com}"
PASSWORD="${PASSWORD:-admin123}"

step() { echo ""; echo "── $1 ──"; }
ok()   { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; exit 1; }

step "Backend health"
curl -sf "$API/health" > /dev/null && ok "GET /health = 200" || fail "/health unreachable"

step "Login"
LOGIN=$(curl -sf -X POST "$API/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
[ -n "$TOKEN" ] && ok "received JWT (${#TOKEN} chars)" || fail "login failed"

step "Authenticated endpoints"
curl -sf -H "Authorization: Bearer $TOKEN" "$API/auth/me" > /dev/null && ok "/auth/me"
curl -sf -H "Authorization: Bearer $TOKEN" "$API/meta/countries?limit=5" > /dev/null && ok "/meta/countries"
curl -sf -H "Authorization: Bearer $TOKEN" "$API/meta/states" > /dev/null && ok "/meta/states"
curl -sf -H "Authorization: Bearer $TOKEN" "$API/meta/hs?limit=5" > /dev/null && ok "/meta/hs"
curl -sf -H "Authorization: Bearer $TOKEN" "$API/dashboards/executive" > /dev/null && ok "/dashboards/executive"
curl -sf -H "Authorization: Bearer $TOKEN" "$API/dashboards/states" > /dev/null && ok "/dashboards/states"
curl -sf -H "Authorization: Bearer $TOKEN" "$API/dashboards/sector/27" > /dev/null && ok "/dashboards/sector/27"
curl -sf -H "Authorization: Bearer $TOKEN" "$API/admin/ingestion/sources" > /dev/null && ok "/admin/ingestion/sources"

step "Auth enforcement"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$API/dashboards/executive")
[ "$HTTP" = "401" ] && ok "unauthenticated request → 401" || fail "expected 401, got $HTTP"

step "Frontend"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$WEB/")
[ "$HTTP" = "200" ] && ok "GET / = 200" || fail "frontend / returned $HTTP"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$WEB/login")
[ "$HTTP" = "200" ] && ok "GET /login = 200" || fail "frontend /login returned $HTTP"

echo ""
echo "All smoke tests passed."
