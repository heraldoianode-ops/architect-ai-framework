#!/bin/bash
# =============================================================================
# ARCHITECT-AI — Push framework a architect-ai-framework
# Ejecutar desde Claude Code en cualquier carpeta vacía
# =============================================================================
set -e
GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${BLUE}→  $1${NC}"; }

REPO_URL="https://github.com/heraldoianode-ops/architect-ai-framework.git"

info "Clonando repositorio..."
git clone "$REPO_URL" architect-ai-framework
cd architect-ai-framework

# ── ESTRUCTURA ────────────────────────────────────────────────────────────────
mkdir -p __AI_CORE__/schemas __AI_CORE__/module_library .git-hooks docs

ok "Estructura de directorios creada"
info "Ver archivos en el repositorio para el contenido completo."
