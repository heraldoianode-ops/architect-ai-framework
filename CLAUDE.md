# ARCHITECT-AI v2.4 — Claude Code Orchestrator

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
ddd.json             → creating/modifying a domain, connector or business feature, or on R16/R17 check
agent_loops.json     → running recursive generation/testing loops or orchestrating sub-agents
rca_protocol.json    → receiving an error report/crash log/bug ticket, or on RCA/AUTORIZO command
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
R17: DDD domain isolation → business rule per domain dir; inter-domain async only (events/abstract connectors); no cross-domain DB/memory access (spec: ddd.json)
R18: Agent loop safety → explicit max_iterations + structured escape routing; recursive loops in isolated git worktree/sandbox (spec: agent_loops.json)
R19: Zero direct env → no process.env or raw config in domain/skill; secrets via Secure Key Broker in infra/connector layer only (spec: ddd.json)
R20: Core file protection → never break core abstractions; extend via dependency injection/composition; new module → replicate architect-ai-modules/templates skeleton + types
R21: RCA Human-in-the-Loop protocol → on error/crash/bug: diagnose, emit RCA report (Symptom, Root Cause, Option A quick / Option B structural), then STOP and wait for explicit human authorization before touching any file (spec: rca_protocol.json)

---

## RCA / Audit Protocol (v2.4 — additive, backward-compatible)
- Full spec in `__AI_CORE__/rca_protocol.json`. Triggered by an error report, crash log, bug ticket, or the `RCA` command.
- **Phase 1 — Diagnosis:** run local diagnostics + architecture impact analysis → emit a Markdown RCA report (Síntoma / Causa Raíz Física / Opción A rápida / Opción B estructural) → **STOP. Do not modify any file.**
- **Checkpoint (authorization):** wait for the human to explicitly write which option they authorize (e.g. `AUTORIZO B`). Never assume or proceed without it.
- **Phase 2 — Isolated repair:** create a `fix/` or `bugfix/` branch → implement the authorized option → run the full test suite → scan changed files for exposed secrets/credentials.
- **Checkpoint (verification):** present the `git diff` and passing test results → wait for the human's visual confirmation before pushing.
- **Phase 3 — Closure:** write the commit/PR using `[Type]: summary` + `SÍNTOMA:` / `CAUSA RAÍZ:` / `SOLUCIÓN:` sections → push the branch → close out the audit log.
- Security isolation: never read or modify files outside the project root; `.env`, SSH keys and OS configuration are always out of bounds (consistent with R19/R20).

---

## DDD + Agent-Loop Architecture (v2.3 — additive, backward-compatible)
- DOMAIN := { Bounded_Context + Ubiquitous_Language + Isolated_Business_Rules } — full spec in `__AI_CORE__/ddd.json`
- Connectors abstract all infra/APIs/DBs (Ports & Adapters + DI). Skills map 1:1 to domain use cases.
- Secure Key Broker = single runtime secret injection point. Source of truth: `services.private.json` (gitignored).
- Sub-agents take atomic roles bound to one domain (Domain_Validator / Domain_Executor / Connector_Adapter) and cannot escape their bounded context.
- Loops: State_Machine + Graph_Based_Execution. Full spec in `__AI_CORE__/agent_loops.json`.

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
RCA [descripción] | AUTORIZO [A|B]

---

## Never
- Greet / apologize
- Read full module library on startup — index only
- Re-read cached paths on every operation
- Mark node COMPLETE without passing minimum tests
- Push to main without explicit user request
- Expose Machine Language to user
- Continue features if critical debt > threshold
- Allow a domain to read another domain's DB/memory directly (R17)
- Invoke process.env or read raw config from a domain/skill — use Secure Key Broker (R19)
- Run an iterative loop without an explicit max_iterations + escape route (R18)
- Break core framework abstractions — extend via DI/composition instead (R20)
- Modify any file during an RCA audit before the human explicitly authorizes Option A or B (R21)
- Push, merge or close an RCA audit without the human's visual confirmation of the diff + passing tests (R21)
- Read or modify files outside the project root, or touch .env/SSH keys/OS config, during an audit (R21)
