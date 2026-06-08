#!/bin/bash
# =============================================================================
# ARCHITECT-AI — Push estructura inicial a architect-ai-modules
# =============================================================================
set -e
GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${BLUE}→  $1${NC}"; }

REPO_URL="https://github.com/heraldoianode-ops/architect-ai-modules.git"

info "Clonando architect-ai-modules..."
git clone "$REPO_URL" architect-ai-modules
cd architect-ai-modules

ok "Ver archivos en el repositorio para el contenido completo."
