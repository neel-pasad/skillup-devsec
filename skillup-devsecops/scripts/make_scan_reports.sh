#!/bin/bash
# Produces the report FILES your teacher asked for (Trivy image scan + SonarQube SAST). Run from the repo root.
# Usage:  IMAGE=skillup:1 SONAR_URL=http://localhost:9000 SONAR_TOKEN=xxxx bash scripts/make_scan_reports.sh
set -u
IMAGE="${IMAGE:-skillup:1}"
OUT="reports"; mkdir -p "$OUT"

echo "== Trivy image scan: $IMAGE"
trivy image --format table -o "$OUT/trivy-image-report.txt" "$IMAGE"
trivy image --format json  -o "$OUT/trivy-image-report.json" "$IMAGE"
TPL=""
for p in /usr/local/share/trivy/templates/html.tpl /usr/share/trivy/templates/html.tpl ./contrib/html.tpl; do [ -f "$p" ] && TPL="$p" && break; done
if [ -n "$TPL" ]; then trivy image --format template --template "@$TPL" -o "$OUT/trivy-image-report.html" "$IMAGE"; else echo "(html template not found - use the .txt/.json reports)"; fi

echo "== Trivy dependency + secret + config scans"
trivy fs --scanners vuln,secret --format table -o "$OUT/trivy-fs-report.txt" .
trivy config --format table -o "$OUT/trivy-config-report.txt" .

if [ -n "${SONAR_TOKEN:-}" ]; then
  echo "== SonarQube export (after sonar-scanner has finished)"
  URL="${SONAR_URL:-http://localhost:9000}"; KEY="skillup-devsecops"
  curl -s -u "$SONAR_TOKEN:" "$URL/api/issues/search?componentKeys=$KEY&ps=500" -o "$OUT/sonar-issues.json"
  curl -s -u "$SONAR_TOKEN:" "$URL/api/measures/component?component=$KEY&metricKeys=bugs,vulnerabilities,code_smells,security_hotspots,coverage,duplicated_lines_density,ncloc" -o "$OUT/sonar-measures.json"
  curl -s -u "$SONAR_TOKEN:" "$URL/api/qualitygates/project_status?projectKey=$KEY" -o "$OUT/sonar-quality-gate.json"
fi
echo "Reports saved in ./$OUT  (also take SonarQube dashboard screenshots)"
