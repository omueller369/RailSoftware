#!/usr/bin/env bash
# Bündelt die notwendigen Schritte für Einrichtung und Aktualisierung der Testumgebung. Vorhandene Daten werden über die vorgesehenen Updatewege erhalten.
# Ubuntu Server 26.04.1 LTS verwendet den gemeinsamen Installer.
set -euo pipefail
exec bash "$(dirname -- "${BASH_SOURCE[0]}")/install.sh" "$@"
