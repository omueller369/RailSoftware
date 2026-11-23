#!/usr/bin/env bash
# Bündelt die notwendigen Schritte für Einrichtung und Aktualisierung der Testumgebung. Vorhandene Daten werden über die vorgesehenen Updatewege erhalten.
# Kompatibler Einstieg für vorhandene Installationsanleitungen.
set -euo pipefail
exec bash "$(dirname -- "${BASH_SOURCE[0]}")/install.sh" "$@"
