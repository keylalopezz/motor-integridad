#!/usr/bin/env bash
# Aplica el changelog de Liquibase y escribe build/liquibase/reporte_liquibase.md.
# Variables: LB_IMAGE, SUPA_URL, SUPA_USER, SUPA_PASS (estas tres opcionales).
set -uo pipefail
mkdir -p build/liquibase
R=build/liquibase/reporte_liquibase.md
FALLOS=0

lb() {  # lb <url> <usuario> <clave> <comando...>
  local url="$1" user="$2" pass="$3"; shift 3
  docker run --rm --network host -v "$PWD/liquibase:/liquibase/changelog" "${LB_IMAGE:-liquibase/liquibase:4.29.2}" \
    --search-path=/liquibase/changelog --changelog-file=db.changelog-master.yaml \
    --url="$url" --username="$user" --password="$pass" "$@"
}

ejecutar() {  # ejecutar <titulo> <url> <usuario> <clave>
  echo "## $1" >> "$R"
  for cmd in "status --verbose" "update" "history"; do
    echo "### liquibase $cmd" >> "$R"
    echo '```text' >> "$R"
    salida=$(lb "$2" "$3" "$4" $cmd 2>&1); codigo=$?
    echo "$salida" | grep -v -E '^#|^\s*$|Liquibase Community|liquibase\.com|Starting Liquibase|Liquibase Version|Get documentation' >> "$R"
    echo '```' >> "$R"
    if [ $codigo -ne 0 ]; then
      echo "**Resultado: error ($codigo)**" >> "$R"; FALLOS=$((FALLOS + 1)); echo "$salida"
    fi
  done
}

{
  echo "# Reporte de ejecuciones de Liquibase"
  echo
  echo "- Fecha: $(date -u '+%Y-%m-%d %H:%M UTC')"
  echo "- Commit: \`${GITHUB_SHA:-local}\`"
  echo "- Changelog: \`liquibase/db.changelog-master.yaml\` (001 esquema inicial, 002 seguridad RLS, 003 eventos de uso)"
  echo
} > "$R"

ejecutar "PostgreSQL de prueba (contenedor)" "jdbc:postgresql://localhost:5432/motor" postgres postgres
if [ -n "${SUPA_URL:-}" ]; then
  ejecutar "Supabase (producción)" "$SUPA_URL" "$SUPA_USER" "$SUPA_PASS"
else
  printf '## Supabase (producción)\nOmitido: configure los secretos LIQUIBASE_URL, LIQUIBASE_USERNAME y LIQUIBASE_PASSWORD.\n' >> "$R"
  echo "::warning::Liquibase solo se aplicó en la base de prueba (faltan los secretos de Supabase)."
fi

echo "Comandos con error: $FALLOS" >> "$R"
[ -n "${GITHUB_STEP_SUMMARY:-}" ] && cat "$R" >> "$GITHUB_STEP_SUMMARY"
cat "$R"
exit $FALLOS
