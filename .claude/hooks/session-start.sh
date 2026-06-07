#!/bin/bash
set -euo pipefail

# Solo ejecutar en entornos remotos de Claude Code
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Instalar gh CLI si no está disponible
if ! command -v gh &>/dev/null; then
  apt-get install -y gh
fi

# Autenticar con GH_TOKEN si está disponible y no hay sesión activa
if [ -n "${GH_TOKEN:-}" ] && ! gh auth status &>/dev/null; then
  echo "$GH_TOKEN" | gh auth login --with-token
fi
