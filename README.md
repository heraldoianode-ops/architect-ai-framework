# ARCHITECT-AI v2.2
## Framework de Desarrollo por Sesiones / Session-Based Development Framework

Marco de trabajo de IA para arquitectos de software. Desarrollo sin escritura manual de código.
AI framework for software architects. Development without manual code writing.

### ES — Inicio rápido / EN — Quick start

```bash
# Clonar este framework para un proyecto nuevo
# Clone this framework for a new project
git clone https://github.com/heraldoianode-ops/architect-ai-framework mi-proyecto
cd mi-proyecto

# Instalar git hooks
cp .git-hooks/pre-commit .git/hooks/pre-commit
cp .git-hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/*

# Iniciar Claude Code — lee CLAUDE.md automáticamente
claude
# → Escribir: INICIAR PROYECTO [nombre]
```

### Estructura / Structure
```
proyecto/
├── CLAUDE.md              ← Boot automático en Claude Code
├── __AI_CORE__/           ← Exclusivo IA — no editar manualmente
│   ├── workflow.json      ← Reglas operativas (v2.2.0)
│   ├── config.json        ← Mapa técnico del proyecto
│   ├── tech_debt.json     ← Deuda técnica
│   ├── features.json      ← Features y backlog
│   ├── decisions.json     ← Decisiones de arquitectura
│   ├── patterns.json      ← Meta-aprendizaje nivel 1
│   ├── health.json        ← Índice de salud (auto-calculado)
│   ├── session_digest.json← Últimas 5 sesiones comprimidas
│   ├── pending_sync.json  ← Cola offline
│   ├── modules.json       ← Módulos instalados
│   ├── services.json      ← Servicios externos
│   └── services.private.json ← Credenciales (en .gitignore)
├── __MODULE_LIBRARY__/    → Ver architect-ai-modules
└── src/                   ← Código del proyecto
```

### Módulos / Modules
[architect-ai-modules](https://github.com/heraldoianode-ops/architect-ai-modules)

### Comandos / Commands
`ARRANCAR` `ESTADO` `TURBO [task]` `INICIAR PROYECTO [name]`
`AUDITAR PROYECTO` `SIGUIENTE` `CERRAR SESIÓN` `SALUD` `REINTENTAR`

---
*ARCHITECT-AI v2.2 — heraldoianode-ops*
