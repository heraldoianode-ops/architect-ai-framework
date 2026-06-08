# ARCHITECT-AI v2
## Framework de Desarrollo por Sesiones para Proyectos de Gran Magnitud
## Session-Based Development Framework for Large-Scale Projects

---

## ES — ¿Qué es esto?
Sistema operativo de IA para desarrollo de software sin escritura de código manual. Diseñado para proyectos de gran magnitud y complejidad, competente con los estándares actuales de la industria. Opera como arquitecto de software senior: toma decisiones técnicas, mantiene coherencia entre sesiones, aprende de patrones y se auto-documenta.

## EN — What is this?
AI operating system for software development without manual code writing. Designed for large-scale and complex projects, compliant with current industry standards. Operates as a senior software architect: makes technical decisions, maintains coherence between sessions, learns from patterns and self-documents.

---

## ES — Estructura del sistema
## EN — System structure

```
ARCHITECT-AI-v2/
│
├── __AI_CORE__/              ← ES: Uso exclusivo de la IA / EN: AI use only
│   ├── config.json           ← ES: Mapa técnico maestro / EN: Master technical map
│   ├── workflow.json         ← ES: Reglas operativas / EN: Operational rules
│   ├── tech_debt.json        ← ES: Deuda técnica / EN: Technical debt
│   ├── features.json         ← ES: Features y backlog / EN: Features and backlog
│   ├── modules.json          ← ES: Registro de módulos / EN: Module registry
│   ├── services.json         ← ES: Servicios externos / EN: External services
│   ├── decisions.json        ← ES: Decisiones de arquitectura / EN: Architecture decisions
│   ├── patterns.json         ← ES: Meta-aprendizaje nivel 1 / EN: Level 1 meta-learning
│   ├── health.json           ← ES: Índice de salud técnica / EN: Technical health index
│   ├── schema.sql            ← ES: Estructura de BD (si aplica) / EN: DB structure (if applicable)
│   └── changelog.md          ← ES: Historial bilingüe / EN: Bilingual history
│
└── __MODULE_LIBRARY__/       ← ES: Compartido entre proyectos / EN: Shared across projects
    ├── meta.json             ← ES: Meta-aprendizaje nivel 2 / EN: Level 2 meta-learning
    └── [categoría]/          ← ES: Módulos reutilizables / EN: Reusable modules
```

---

## ES — Comandos principales
## EN — Main commands

| Comando / Command | ES | EN |
|---|---|---|
| `ARRANCAR` | Cargar contexto e iniciar sesión | Load context and start session |
| `ESTADO` | Dashboard del proyecto | Project dashboard |
| `INICIAR PROYECTO [nombre]` | Nuevo proyecto con acuerdo inicial | New project with initial agreement |
| `AUDITAR PROYECTO` | Mapear proyecto heredado | Map inherited project |
| `SIGUIENTE` | Continuar fragmento pendiente | Continue pending fragment |
| `CERRAR SESIÓN` | Cierre + SNAP FINAL automático | Close + automatic FINAL SNAP |
| `INSTALAR MÓDULO [id]` | Descargar módulo del library | Download module from library |
| `PUBLICAR MÓDULO [fn]` | Subir función al library | Upload function to library |
| `SALUD` | Índice de salud técnica | Technical health index |
| `REINTENTAR` | Reintentar tras servicio caído | Retry after service recovery |

---

## ES — Reglas operativas clave
## EN — Key operational rules

**R1** ES: Conflicto entre archivos → verificar contra código → preguntar al usuario.
**R1** EN: File conflict → verify against code → ask user.

**R2** ES: Rama incorrecta → aviso + rama definida una sola vez → pase a main solo por solicitud.
**R2** EN: Wrong branch → warning + branch defined once → merge to main only on request.

**R3** ES: Nodos y fases definidos en acuerdo previo al inicio.
**R3** EN: Nodes and phases defined in agreement prior to start.

**R4** ES: ENV nueva → buscar si ya existe → crear y avisar.
**R4** EN: New ENV → check if exists → create and notify.

**R5** ES: Breaking change → deprecar viejo → crear nuevo → migrar → eliminar.
**R5** EN: Breaking change → deprecate old → create new → migrate → delete.

**R6** ES: Toda documentación en ES y EN. Código en EN. Commits en EN.
**R6** EN: All documentation in ES and EN. Code in EN. Commits in EN.

**R7** ES: Módulo desactualizado → actualizar library inmediatamente → continuar.
**R7** EN: Outdated module → update library immediately → continue.

**R8** ES: Tests mínimos por pirámide alineada (L1/L2/L3). Nodo COMPLETE solo si tests pasan.
**R8** EN: Minimum tests by aligned pyramid (L1/L2/L3). Node COMPLETE only if tests pass.

**R9** ES: Servicio caído → frenar todo → esperar → reintentar con REINTENTAR.
**R9** EN: Service down → stop everything → wait → retry with RETRY.

**R10** ES: MAJOR solo si breaking change → probar → subir si todo funciona.
**R10** EN: MAJOR only on breaking change → test → increment if everything works.

---

## ES — Auto-guardado (3 capas)
## EN — Auto-save (3 layers)

**Capa 1 / Layer 1** — Por hito / Milestone: delta inmediato al completar unidad de trabajo.
**Capa 2 / Layer 2** — Predictivo / Predictive: SNAP automático cuando tokens < 20%.
**Capa 3 / Layer 3** — Cierre / Session end: SNAP FINAL bilingüe completo. Commit automático si GitHub MCP conectado.

---

## ES — Meta-aprendizaje
## EN — Meta-learning

**Nivel 1 / Level 1** — `patterns.json`: aprende del proyecto actual. Bugs recurrentes, módulos volátiles, decisiones revertidas.

**Nivel 2 / Level 2** — `__MODULE_LIBRARY__/meta.json`: aprende entre proyectos. Activo desde el segundo proyecto. Deudas universales, fases subestimadas, módulos más reutilizados.

---

## ES — Para la SaaS
## EN — For the SaaS

Cada proyecto tiene su propio `__AI_CORE__/` aislado.
El `__MODULE_LIBRARY__/` es compartido entre todos los proyectos.
El `meta.json` acumula inteligencia operativa de toda la SaaS.

Each project has its own isolated `__AI_CORE__/`.
The `__MODULE_LIBRARY__/` is shared across all projects.
The `meta.json` accumulates operational intelligence from the entire SaaS.

---

*ARCHITECT-AI v2 — Framework operativo de desarrollo sin código manual.*
*ARCHITECT-AI v2 — Operational development framework without manual coding.*
