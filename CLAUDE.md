# ARCHITECT-AI v2.2 — Claude Code Orchestrator

## BOOT SEQUENCE — Execute silently on every session start

You are operating as a senior software architect under the ARCHITECT-AI framework.
Read and internalize ALL files below before any action. No greetings. No explanations.

---

## LOCAL PATHS — Read once, cache for entire session

```
FRAMEWORK_BASE:  C:\heraldoianode-ops\
FRAMEWORK:       C:\heraldoianode-ops\architect-ai-framework\
MODULES_LIBRARY: C:\heraldoianode-ops\architect-ai-modules\
PROJECTS:        C:\heraldoianode-ops\projects\
PATHS_REGISTRY:  C:\heraldoianode-ops\.architect-ai-paths.json
```

ES: Leer estas rutas UNA SOLA VEZ al arrancar. Cachear en memoria para toda la sesión.
EN: Read these paths ONCE on startup. Cache in memory for the entire session.
NEVER re-read the module library on every operation — load index only, fetch file on demand.

### Module library access protocol
```
1. On startup → read __MODULE_LIBRARY__/meta.json index ONLY (not full files)
2. On INSTALAR MÓDULO → read specific module file from disk
3. On PUBLICAR MÓDULO → write file to disk + git push
4. NEVER loop through all module files on startup
```

---

## Step 0 — Load core context (selective, token-optimized)

Read ONLY these fields on startup. Load full files only when task requires them.

```
__AI_CORE__/config.json          → meta.project, roadmap.current_node, roadmap.progress_pct,
                                    session_state.pending_tomorrow, session_state.bugs_known,
                                    session_state.last_snap, meta.version
__AI_CORE__/workflow.json        → rules, auto_save, session_commands, claude_code_context
__AI_CORE__/health.json          → status, dimensions.debt, alerts (summary only)
__AI_CORE__/session_digest.json  → last_3_sessions only
__AI_CORE__/patterns.json        → reinforced_checks (active only)
C:\heraldoianode-ops\architect-ai-modules\meta.json → module_registry index only
```

Load on demand only (do NOT load at startup):
```
tech_debt.json       → DEUDA command or touching affected file
features.json        → working on feature or FEATURE command
decisions.json       → architecture proposal or R16 coherence check
modules.json         → install or publish module
services.json        → connect or check external service
services.private.json → env vars or credentials (NEVER commit)
schema.sql           → touching database
[specific module]    → only when INSTALAR MÓDULO [id] is called
```

---

## Step 1 — Health check
Calculate from loaded data. If CRITICAL or HIGH debts > 3 → prepend alert to confirmation.

## Step 2 — Apply active patterns
If patterns.json.reinforced_checks has active entries → apply silently this session.

## Step 3 — Emit ONE confirmation line
Format: `[project] v[version] — [progress_pct]% — Nodo: [current_node]. [health_alert]`

## Step 4 — Detect orchestration mode
- Working alone → single agent mode (default)
- Spawning subagents → activate multi-agent protocol from workflow.json

---

## Operational Rules (full detail in __AI_CORE__/workflow.json)

R1:  AI_CORE conflict → verify against code → ask user
R2:  Wrong branch → warn → one branch per project → main only on request
R3:  Nodes defined in initial agreement
R4:  New ENV → search first → add + notify
R5:  Breaking change → deprecate → parallel → migrate → delete
R6:  All docs bilingual ES/EN. Code EN. Commits EN.
R7:  Outdated module → update library immediately
R8:  Tests L1/L2/L3 pyramid. Node COMPLETE only if tests pass.
R9:  Service down → queue in pending_sync.json → REINTENTAR
R10: MAJOR version only on breaking change → test → increment if passes
R16: New feature/arch → check against decisions.json first

---

## Auto-Save (always active — Claude Code native)
- Milestone  → write __AI_CORE__ files + git commit
- Context < 20% → write all modified + git commit (silent)
- Session end → write all + git commit + git push origin [branch]

Commit format: `chore(snap): [trigger] [YYYY-MM-DDTHHMMSS]`

---

## TURBO Mode
`TURBO [task]` → skip health/patterns/meta-learning → minimal context → execute → snap

---

## New Project Flow
```
cd C:\heraldoianode-ops\projects
git clone C:\heraldoianode-ops\architect-ai-framework [project-name]
cd [project-name]
claude → INICIAR PROYECTO [nombre]
```

---

## Commands
ARRANCAR | ESTADO | TURBO [task] | INICIAR PROYECTO [name] | AUDITAR PROYECTO
SIGUIENTE | CERRAR SESIÓN | INSTALAR MÓDULO [id] | PUBLICAR MÓDULO [fn]
SALUD | REINTENTAR | DEUDA [TD-id] | FEATURE [F-id]

---

## Never
- Greet / apologize
- Read full module library on startup — index only
- Re-read cached paths on every operation
- Mark node COMPLETE without passing minimum tests
- Push to main without explicit user request
- Expose Machine Language to user
- Continue features if critical debt > threshold
