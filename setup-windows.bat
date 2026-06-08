@echo off
:: =============================================================================
:: ARCHITECT-AI v2.2 — Setup inicial en Windows
:: ES: Doble click para ejecutar. No requiere configuracion especial.
:: EN: Double click to run. No special configuration required.
:: =============================================================================

title ARCHITECT-AI v2.2 — Windows Setup
color 0A

echo.
echo ==========================================================
echo    ARCHITECT-AI v2.2 -- Windows Setup
echo ==========================================================
echo.

:: ── VERIFICAR GIT ────────────────────────────────────────────────────────────
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] git no encontrado.
    echo         Instalar desde: https://git-scm.com/download/win
    echo         Luego volver a ejecutar este archivo.
    pause
    exit /b 1
)
echo [OK] git disponible

:: ── RUTA BASE FIJA ───────────────────────────────────────────────────────────
set BASE_PATH=C:\heraldoianode-ops

echo.
echo [INFO] Ruta base del framework: %BASE_PATH%
echo        Todos los repos se instalaran aqui.
echo        Nunca en Desktop ni Downloads.
echo.
set /p CONFIRM="Confirmar ruta %BASE_PATH%? [S/N]: "
if /i not "%CONFIRM%"=="S" (
    set /p BASE_PATH="Ingresa la ruta que preferis (ej: D:\mis-proyectos): "
)

:: ── CREAR CARPETA BASE ───────────────────────────────────────────────────────
if not exist "%BASE_PATH%" (
    mkdir "%BASE_PATH%"
    echo [OK] Carpeta creada: %BASE_PATH%
) else (
    echo [OK] Carpeta ya existe: %BASE_PATH%
)

cd /d "%BASE_PATH%"

:: ── CLONAR REPOS ─────────────────────────────────────────────────────────────
echo.
echo [INFO] Clonando architect-ai-framework...
if exist "%BASE_PATH%\architect-ai-framework" (
    echo [INFO] Ya existe. Actualizando...
    cd /d "%BASE_PATH%\architect-ai-framework"
    git pull -q origin main
    cd /d "%BASE_PATH%"
) else (
    git clone https://github.com/heraldoianode-ops/architect-ai-framework architect-ai-framework
)
echo [OK] architect-ai-framework instalado

echo.
echo [INFO] Clonando architect-ai-modules...
if exist "%BASE_PATH%\architect-ai-modules" (
    echo [INFO] Ya existe. Actualizando...
    cd /d "%BASE_PATH%\architect-ai-modules"
    git pull -q origin main
    cd /d "%BASE_PATH%"
) else (
    git clone https://github.com/heraldoianode-ops/architect-ai-modules architect-ai-modules
)
echo [OK] architect-ai-modules instalado

:: ── CREAR CARPETA DE PROYECTOS ───────────────────────────────────────────────
if not exist "%BASE_PATH%\projects" (
    mkdir "%BASE_PATH%\projects"
)
echo [OK] Carpeta de proyectos: %BASE_PATH%\projects

:: ── REGISTRAR RUTAS ──────────────────────────────────────────────────────────
echo {> "%BASE_PATH%\.architect-ai-paths.json"
echo   "base_path": "%BASE_PATH%",>> "%BASE_PATH%\.architect-ai-paths.json"
echo   "framework": "%BASE_PATH%\\architect-ai-framework",>> "%BASE_PATH%\.architect-ai-paths.json"
echo   "modules": "%BASE_PATH%\\architect-ai-modules",>> "%BASE_PATH%\.architect-ai-paths.json"
echo   "projects": "%BASE_PATH%\\projects",>> "%BASE_PATH%\.architect-ai-paths.json"
echo   "org": "heraldoianode-ops">> "%BASE_PATH%\.architect-ai-paths.json"
echo }>> "%BASE_PATH%\.architect-ai-paths.json"
echo [OK] Rutas registradas en .architect-ai-paths.json

:: ── INSTALAR GIT HOOKS ───────────────────────────────────────────────────────
if exist "%BASE_PATH%\architect-ai-framework\.git-hooks\pre-commit" (
    copy /Y "%BASE_PATH%\architect-ai-framework\.git-hooks\pre-commit"  "%BASE_PATH%\architect-ai-framework\.git\hooks\pre-commit" >nul
    copy /Y "%BASE_PATH%\architect-ai-framework\.git-hooks\post-commit" "%BASE_PATH%\architect-ai-framework\.git\hooks\post-commit" >nul
    echo [OK] Git hooks instalados
)

:: ── RESULTADO FINAL ──────────────────────────────────────────────────────────
echo.
echo ==========================================================
echo    OK  SETUP COMPLETO
echo ==========================================================
echo.
echo   %BASE_PATH%\
echo   +-- architect-ai-framework\   (plantilla base)
echo   +-- architect-ai-modules\     (library compartido)
echo   +-- projects\                 (aqui van los proyectos)
echo   +-- .architect-ai-paths.json  (registro de rutas)
echo.
echo [INFO] Para iniciar un proyecto nuevo:
echo.
echo   1. Abrir Claude Code
echo   2. cd %BASE_PATH%\projects
echo   3. git clone %BASE_PATH%\architect-ai-framework nombre-proyecto
echo   4. cd nombre-proyecto
echo   5. claude
echo   6. Escribir: INICIAR PROYECTO [nombre]
echo.
pause
