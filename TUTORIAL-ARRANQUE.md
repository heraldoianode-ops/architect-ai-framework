# ARCHITECT-AI v2.2
## Tutorial de Arranque / Startup Tutorial
### heraldoianode-ops

---

# PARTE 1 — INSTALACIÓN INICIAL
# PART 1 — INITIAL INSTALLATION
### ES: Se hace UNA SOLA VEZ en tu PC. / EN: Done ONCE on your PC.

---

## Paso 1 — Requisitos previos / Step 1 — Prerequisites

Verificar que tenés instalado:

| Herramienta | Descarga | Para qué sirve |
|---|---|---|
| **Git** | https://git-scm.com/download/win | Control de versiones |
| **Claude Code** | https://claude.ai/code | Orquestador IA |
| **Node.js** (opcional) | https://nodejs.org | Si tu proyecto es JS/TS |

Para verificar, abrís una terminal y escribís:
```bash
git --version
claude --version
```
Si ambos responden con un número de versión → listo.

---

## Paso 2 — Ejecutar el setup / Step 2 — Run setup

1. Descargás `setup-windows.bat` desde el repo:
   ```
   https://github.com/heraldoianode-ops/architect-ai-framework
   ```

2. **Doble click** en `setup-windows.bat`

3. Aparece una ventana negra. Cuando pregunte confirmás con `S` + Enter

4. El script hace todo solo:
   - Crea `C:\heraldoianode-ops\`
   - Clona `architect-ai-framework`
   - Clona `architect-ai-modules`
   - Crea carpeta `projects\`
   - Registra las rutas en `.architect-ai-paths.json`

5. Al terminar verás:
   ```
   OK  SETUP COMPLETO
   C:\heraldoianode-ops\
   +-- architect-ai-framework\
   +-- architect-ai-modules\
   +-- projects\
   +-- .architect-ai-paths.json
   ```

---

## Resultado en tu PC / Result on your PC

```
C:\heraldoianode-ops\
├── architect-ai-framework\   ← plantilla base (no tocar)
├── architect-ai-modules\     ← library de módulos compartido
├── projects\                 ← AQUÍ van todos tus proyectos
└── .architect-ai-paths.json  ← registro de rutas
```

---
---

# PARTE 2 — INICIAR UN PROYECTO NUEVO
# PART 2 — START A NEW PROJECT
### ES: Se hace UNA VEZ por cada programa nuevo. / EN: Done ONCE per new program.

---

## Paso 1 — Crear repositorio en GitHub

1. Ir a https://github.com/new
2. Nombre del repo: `nombre-de-tu-proyecto`
3. Visibilidad: Private (recomendado) o Public
4. **NO** inicializar con README — dejarlo vacío
5. Click en **Create repository**
6. Copiar la URL: `https://github.com/heraldoianode-ops/nombre-de-tu-proyecto.git`

---

## Paso 2 — Clonar el framework como base

Abrís una terminal (CMD o PowerShell) y escribís:

```bash
cd C:\heraldoianode-ops\projects
git clone C:\heraldoianode-ops\architect-ai-framework nombre-de-tu-proyecto
cd nombre-de-tu-proyecto
```

---

## Paso 3 — Conectar al repo de GitHub

```bash
git remote remove origin
git remote add origin https://github.com/heraldoianode-ops/nombre-de-tu-proyecto.git
git push -u origin main
```

---

## Paso 4 — Instalar git hooks

```bash
copy .git-hooks\pre-commit  .git\hooks\pre-commit
copy .git-hooks\post-commit .git\hooks\post-commit
```

---

## Paso 5 — Abrir Claude Code

```bash
claude
```

Claude Code lee `CLAUDE.md` automáticamente y responde con algo así:
```
[sin-nombre] v0.1.0 — 0% — Nodo: sin definir. Esperando acuerdo inicial.
```

---

## Paso 6 — Iniciar el proyecto

Escribís en Claude Code:
```
INICIAR PROYECTO nombre-de-tu-proyecto
```

Claude Code te hace preguntas en orden. Respondés cada una:

```
Tipo de proyecto:
  1) SaaS Web
  2) API REST
  3) App Mobile iOS+Android
  4) App Escritorio Windows
  5) Fullstack Next.js
  6) Librería NPM
  7) Personalizado
→ Escribís el número

¿Es para cliente externo, producto interno, o ambos?
→ externo / interno / ambos

[Si externo] Nombre del cliente:
→ escribís el nombre

Stack sugerido para SaaS Web:
  Frontend: React 18 + Vite — ¿confirmar? [S/N]
  Backend: Netlify Functions — ¿confirmar? [S/N]
  ...

URL del repositorio GitHub:
→ https://github.com/heraldoianode-ops/nombre-de-tu-proyecto

Rama de desarrollo (default: develop):
→ Enter para aceptar develop

Fases propuestas:
  Fase 1 — Setup e Infraestructura (~2 días) ¿confirmar? [S/N]
    Nodo 1.1 — Inicialización del repo (~3hs) [L1] ¿confirmar? [S/N]
    ...
→ confirmás o ajustás cada una
```

Al terminar Claude Code escribe todos los archivos `__AI_CORE__` y hace el primer commit:
```
feat(init): project agreement — nombre-de-tu-proyecto
[nombre-de-tu-proyecto] v0.1.0 — 0% — Nodo: 1.1 — Setup repo. Arrancamos.
```

---
---

# PARTE 3 — SESIÓN DE TRABAJO DIARIA
# PART 3 — DAILY WORK SESSION
### ES: Lo que hacés cada vez que trabajás. / EN: What you do every time you work.

---

## Arrancar una sesión

```bash
cd C:\heraldoianode-ops\projects\nombre-de-tu-proyecto
claude
```

Claude Code lee el contexto automáticamente y responde:
```
nombre-proyecto v0.3.1 — 34% — Nodo: 2.3 — Flujo de recuperación. Sin alertas críticas.
```

Listo. Podés empezar a trabajar directamente.

---

## Comandos del día a día

| Comando | Cuándo usarlo |
|---|---|
| `ESTADO` | Ver dashboard completo del proyecto |
| `SIGUIENTE` | Continuar fragmento que quedó a mitad |
| `TURBO [tarea]` | Tarea pequeña y rápida, menos de 15 minutos |
| `SALUD` | Ver índice de salud técnica |
| `DEUDA TD-001` | Ver detalle de una deuda técnica |
| `FEATURE F-012` | Ver detalle de una feature |
| `REINTENTAR` | Si un servicio estaba caído y volvió |

---

## Cerrar una sesión

Cuando terminás de trabajar escribís:
```
CERRAR SESIÓN
```

Claude Code automáticamente:
1. Escribe todos los archivos `__AI_CORE__` actualizados
2. Hace commit: `chore(snap): session end [2026-06-08T183000]`
3. Hace push al branch del proyecto
4. Muestra resumen: completado hoy, pendiente mañana, próximo nodo

O si decís naturalmente "listo por hoy", "hasta mañana", "cerramos" — lo detecta y hace el SNAP solo.

---

## Tarea rápida sin contexto completo

Para cosas pequeñas como "agrega un campo al formulario" o "corrige este typo":
```
TURBO agrega campo teléfono al formulario de registro
```
Carga mínimo contexto, ejecuta, hace snap al terminar.

---
---

# PARTE 4 — MÓDULOS REUTILIZABLES
# PART 4 — REUSABLE MODULES
### ES: Compartir código entre proyectos. / EN: Share code between projects.

---

## Instalar un módulo en tu proyecto

```
INSTALAR MÓDULO MOD-auth-001
```

Claude Code copia el módulo desde `C:\heraldoianode-ops\architect-ai-modules\` al proyecto.

---

## Publicar una función al library

Cuando escribís una función genérica reutilizable:
```
PUBLICAR MÓDULO validateEmail
```

Claude Code:
1. Extrae la función
2. Genera documentación bilingüe
3. La copia a `architect-ai-modules\utils\`
4. Hace commit en el library

Disponible para todos los proyectos futuros.

---
---

# PARTE 5 — REFERENCIA RÁPIDA
# PART 5 — QUICK REFERENCE

---

## Estructura de carpetas

```
C:\heraldoianode-ops\
├── architect-ai-framework\      ← plantilla (no tocar)
├── architect-ai-modules\        ← library compartido
│   ├── auth\
│   ├── email\
│   ├── payments\
│   ├── database\
│   ├── api\
│   ├── ui\
│   ├── utils\
│   ├── devops\
│   ├── windows\
│   └── meta.json
└── projects\
    ├── proyecto-alpha\
    │   ├── CLAUDE.md
    │   ├── __AI_CORE__\
    │   │   ├── workflow.json
    │   │   ├── config.json
    │   │   ├── tech_debt.json
    │   │   ├── features.json
    │   │   ├── decisions.json
    │   │   ├── patterns.json
    │   │   ├── health.json
    │   │   ├── session_digest.json
    │   │   ├── pending_sync.json
    │   │   ├── modules.json
    │   │   ├── services.json
    │   │   └── services.private.json  ← NUNCA al repo
    │   └── src\
    └── proyecto-beta\
        └── ...
```

---

## Todos los comandos

| Comando | Descripción |
|---|---|
| `ARRANCAR` | Forzar recarga de contexto |
| `ESTADO` | Dashboard ANSI del proyecto |
| `TURBO [tarea]` | Tarea atómica sin contexto completo |
| `INICIAR PROYECTO [nombre]` | Nuevo proyecto — acuerdo inicial |
| `AUDITAR PROYECTO` | Mapear proyecto heredado existente |
| `SIGUIENTE` | Continuar fragmento pendiente |
| `CERRAR SESIÓN` | SNAP final + commit + push |
| `INSTALAR MÓDULO [id]` | Traer módulo del library |
| `PUBLICAR MÓDULO [función]` | Subir función al library |
| `SALUD` | Índice de salud técnica |
| `REINTENTAR` | Procesar cola offline |
| `DEUDA [TD-id]` | Detalle de deuda técnica |
| `FEATURE [F-id]` | Detalle de feature |

---

## Reglas que siempre aplican

| Regla | Qué hace |
|---|---|
| **R2** | Nunca trabaja en `main` — siempre en la rama del proyecto |
| **R6** | Todo documento en español E inglés |
| **R8** | Nodo COMPLETE solo si los tests pasan |
| **R9** | Si un servicio cae → para todo, encola, espera `REINTENTAR` |
| **Auto-save** | Guarda y commitea solo — nunca perdés trabajo |

---

## Repositorios del framework

| Repo | URL | Para qué |
|---|---|---|
| Framework | https://github.com/heraldoianode-ops/architect-ai-framework | Plantilla base |
| Módulos | https://github.com/heraldoianode-ops/architect-ai-modules | Library compartido |

---

## Ante cualquier duda

En Claude Code escribís en lenguaje natural lo que necesitás.
Claude Code lo interpreta, ejecuta y documenta solo.

```
"necesito agregar autenticación con Google"
"el deploy a Netlify está fallando"
"muéstrame el estado de las deudas técnicas"
"quiero empezar la fase 3"
```

---

*ARCHITECT-AI v2.2 — heraldoianode-ops*
*Framework operativo de desarrollo sin código manual.*
*Operational development framework without manual coding.*