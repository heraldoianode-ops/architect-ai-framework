#!/usr/bin/env bash
# Autentica el GitHub CLI (gh) desde cualquier carpeta del sistema.
# Uso: bash scripts/setup-github-auth.sh

set -euo pipefail

# ── Verificar que gh está instalado ─────────────────────────────────────────
if ! command -v gh &>/dev/null; then
  echo "Error: GitHub CLI (gh) no está instalado."
  echo "Instálalo desde https://cli.github.com y vuelve a ejecutar este script."
  exit 1
fi

# ── Verificar si ya hay sesión activa ────────────────────────────────────────
if gh auth status &>/dev/null; then
  echo "Ya estás autenticado:"
  gh auth status
  exit 0
fi

# ── Iniciar autenticación ────────────────────────────────────────────────────
echo "Iniciando autenticación con GitHub CLI..."
echo "Puedes ejecutar este script desde cualquier carpeta, por ejemplo:"
echo "  cd ~"
echo "  gh auth login"
echo ""

gh auth login

echo ""
echo "Autenticación completada. Estado actual:"
gh auth status
