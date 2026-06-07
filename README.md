# architect-ai-framework

Contiene todo lo que construimos. Es la plantilla base que se copia a cada proyecto nuevo.

## Configuración inicial

### 1. Autenticar GitHub CLI

Antes de clonar o usar cualquier proyecto, autentica el GitHub CLI desde cualquier carpeta:

```bash
# Desde cualquier carpeta, por ejemplo:
cd ~
gh auth login
```

O usa el script incluido en esta plantilla:

```bash
bash scripts/setup-github-auth.sh
```

El script verifica si ya hay sesión activa antes de lanzar el flujo de autenticación.

### 2. Verificar autenticación

```bash
gh auth status
```

## Estructura

```
.
├── scripts/
│   └── setup-github-auth.sh   # Autenticación de GitHub CLI
└── README.md
```
