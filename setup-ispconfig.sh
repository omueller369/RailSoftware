#!/usr/bin/env bash
# Bündelt die notwendigen Schritte für Einrichtung und Aktualisierung der Testumgebung. Vorhandene Daten werden über die vorgesehenen Updatewege erhalten.
# Nur die Anwendung auf einem vorhandenen Ubuntu-/ISPConfig-Server einrichten.
set -Eeuo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
command -v python3 >/dev/null || { echo 'FEHLER: Python 3 fehlt. Keine Serverpakete wurden installiert.' >&2; exit 1; }
exec python3 "$project_root/setup/ispconfig_install.py" "$@"
