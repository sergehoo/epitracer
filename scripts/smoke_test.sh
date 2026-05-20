#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Smoke test EpidemiTracker — vérifie qu'un déploiement local fonctionne.
# Utilisable contre la stack `docker compose -f docker-compose.yml -f docker-compose.local.yml`.
#
# Usage :
#   bash scripts/smoke_test.sh
#   bash scripts/smoke_test.sh http://localhost:8000 http://publictraveler.lvh.me http://inhpadmin.lvh.me
# ---------------------------------------------------------------------------
set -u

API=${1:-http://api.lvh.me}
PUBLIC=${2:-http://publictraveler.lvh.me}
ADMIN=${3:-http://inhpadmin.lvh.me}

ok()  { printf "  \033[32m✓\033[0m %s\n" "$1"; }
ko()  { printf "  \033[31m✗\033[0m %s\n" "$1"; FAILED=1; }
hr()  { printf "\n\033[1m== %s ==\033[0m\n" "$1"; }

FAILED=0

hr "Backend Django"
code=$(curl -s -o /dev/null -w "%{http_code}" "$API/healthz/")
[[ "$code" == "200" ]] && ok "healthz 200" || ko "healthz $code"

code=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/schema/")
[[ "$code" == "200" ]] && ok "OpenAPI schema servi" || ko "OpenAPI $code"

code=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/v1/passes/public-key.pem")
[[ "$code" == "200" ]] && ok "Clé publique Ed25519 publiée" || ko "Clé publique $code"

hr "Catalogue maladies (auth requise) → 401 attendu"
code=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/v1/diseases/")
[[ "$code" == "401" ]] && ok "401 sans token (RBAC OK)" || ko "Attendu 401, reçu $code"

hr "Endpoint public : enregistrement voyageur (Section INHP)"
RESP=$(curl -s -X POST -H "Content-Type: application/json" \
  "$API/api/v1/ebola/public/register/" \
  -d '{
    "voyage": {
      "arrival_date": "2026-05-20",
      "transport_mode": "plane",
      "flight_or_voyage_number": "AF572",
      "seat_number": "14A",
      "entry_point_code": "ABJ-AIRPORT"
    },
    "identite": {
      "last_name": "TEST", "first_name": "Smoke",
      "age": 30, "age_unit": "years",
      "gender": "M", "profession": "Ingénieur",
      "id_document_type": "passport", "id_document_number": "P987654",
      "nationality_code": "CI",
      "phone_mobile": "+22507000000", "email": "smoke@test.ci",
      "postal_address": "BP 1234 Abidjan"
    },
    "historique": [
      {"role": "origin", "country_code": "CD", "city": "Goma", "duration_text": "10 jours"}
    ],
    "confinement": {
      "city": "Abidjan", "commune": "Cocody", "neighborhood": "II Plateaux",
      "emergency_phone_ci": "+22507111111"
    },
    "exposure": {
      "visited_ebola_zone": true,
      "visited_ebola_zone_details": "Goma, RDC",
      "contact_with_case": false,
      "attended_funeral_or_touched_corpse": false,
      "visited_ebola_healthcare_facility": false
    },
    "symptoms": {
      "fever": false, "intense_fatigue": false, "muscle_joint_pain": false,
      "severe_headache": false, "sore_throat_or_abdominal": false,
      "diarrhea_nausea_vomiting": false, "unexplained_bleeding": false
    },
    "declaration": {
      "signed_place": "Abidjan",
      "declared_at": "2026-05-20T10:00:00Z",
      "declarant_full_name": "TEST Smoke",
      "truthful_declaration": true
    }
  }')

PID=$(echo "$RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('traveler',{}).get('public_id','')) " 2>/dev/null)
SCORE=$(echo "$RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('investigation',{}).get('risk_score','')) " 2>/dev/null)
LEVEL=$(echo "$RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('investigation',{}).get('risk_level','')) " 2>/dev/null)
PASS_NUM=$(echo "$RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('pass',{}).get('pass_number','')) " 2>/dev/null)
TOKEN=$(echo "$RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('pass',{}).get('qr_token','')) " 2>/dev/null)

if [[ -n "$PID" ]]; then
  ok "Voyageur créé : $PID (score=$SCORE, niveau=$LEVEL)"
  ok "Pass émis : $PASS_NUM"
else
  ko "Réponse inattendue : $(echo "$RESP" | head -c 200)"
fi

hr "Consultation publique du pass"
code=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/v1/ebola/public/pass/$PID/")
[[ "$code" == "200" ]] && ok "GET /ebola/public/pass/$PID/" || ko "Pass consult $code"

hr "Vérification du QR (signature Ed25519)"
if [[ -n "$TOKEN" ]]; then
  RES=$(curl -s -X POST -H "Content-Type: application/json" \
    "$API/api/v1/passes/verify/" \
    -d "{\"token\": \"$TOKEN\", \"online\": true}")
  VALID=$(echo "$RES" | python3 -c "import sys, json; print(json.load(sys.stdin).get('is_valid'))" 2>/dev/null)
  [[ "$VALID" == "True" ]] && ok "QR validé crypto + online" || ko "QR invalide : $RES"
fi

hr "Frontend : séparation par hostname"
# Le portail public doit servir / (200), pas /dashboard (redirect 308 vers admin)
code=$(curl -s -o /dev/null -w "%{http_code}" "$PUBLIC/")
[[ "$code" == "200" ]] && ok "publictraveler.lvh.me/ → 200" || ko "Public / : $code"

code=$(curl -s -o /dev/null -w "%{http_code}" "$PUBLIC/voyageur")
[[ "$code" == "200" ]] && ok "publictraveler.lvh.me/voyageur → 200" || ko "Public /voyageur : $code"

code=$(curl -s -o /dev/null -w "%{http_code}" "$PUBLIC/dashboard")
[[ "$code" == "308" || "$code" == "307" ]] && ok "publictraveler.lvh.me/dashboard → redirect cross-domain" \
  || ko "Public /dashboard devrait rediriger, reçu $code"

code=$(curl -s -o /dev/null -w "%{http_code}" "$ADMIN/")
[[ "$code" == "308" || "$code" == "307" ]] && ok "inhpadmin.lvh.me/ → redirect /dashboard" \
  || ko "Admin / devrait rediriger, reçu $code"

code=$(curl -s -o /dev/null -w "%{http_code}" "$ADMIN/auth/login")
[[ "$code" == "200" ]] && ok "inhpadmin.lvh.me/auth/login → 200" || ko "Admin /auth/login : $code"

code=$(curl -s -o /dev/null -w "%{http_code}" "$ADMIN/voyageur")
[[ "$code" == "308" || "$code" == "307" ]] && ok "inhpadmin.lvh.me/voyageur → redirect vers public" \
  || ko "Admin /voyageur devrait rediriger, reçu $code"

hr "Résultat"
if [[ $FAILED -eq 0 ]]; then
  printf "\033[32mTous les smoke tests sont passés.\033[0m\n"
else
  printf "\033[31mDes tests ont échoué — vérifier les logs des conteneurs.\033[0m\n"
  exit 1
fi
