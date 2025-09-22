# Plan de Desarrollo: Agente Especializado Asíncrono (AEA)

El objetivo es crear un framework para lanzar agentes que operen de forma autónoma en un directorio específico, sigan un plan, se comuniquen de forma asíncrona y mantengan un contexto ligero.

---

### **Fase 1: Definición de la Arquitectura y Configuración**

Aquí sentamos las bases. La clave es la configuración para hacer que cada agente sea reutilizable.

1.  **Estructura de Directorios:**
    Crearemos una carpeta para nuestro framework AEA.

    ```
    /Users/rhayalcantara/proyectos/aea_framework/
    ├── main.py             # El punto de entrada para iniciar un agente.
    ├── agent_config.toml   # ¡Clave! Aquí se define la personalidad y tarea del agente.
    ├── core/
    │   ├── agent.py        # El cerebro del agente, su bucle de vida.
    │   └── state.py        # Gestiona el estado interno del agente.
    ├── mcp/
    │   └── queue_manager.py # Lógica para leer y escribir en las colas de mensajes.
    └── tools/
        ├── shell.py        # Herramienta para ejecutar comandos de terminal.
        ├── git.py          # Herramientas para commit, push, etc.
        └── filesystem.py   # Herramientas para leer/escribir archivos.
    ```

2.  **Archivo de Configuración (`agent_config.toml`):**
    Usaremos el formato TOML por ser muy legible. Este archivo es el "ADN" de cada agente.

    ```toml
    # agent_config.toml

    [identity]
    name = "frontend-builder"
    role = "Compilar el frontend de producción y preparar para despliegue."

    [environment]
    working_dir = "/Users/rhayalcantara/proyectos/mi-app-frontend"

    [communication]
    # Archivos que simulan nuestras colas de mensajes
    orchestrator_queue = "/Users/rhayalcantara/proyectos/queues/frontend_in.json"
    agent_queue = "/Users/rhayalcantara/proyectos/queues/frontend_out.json"

    [plan]
    # El plan de alto nivel que debe seguir el agente
    objective = "Realizar el build de producción, versionarlo con Git y notificar."
    tasks = [
        "Verificar que no haya cambios sin guardar.",
        "Instalar dependencias con 'npm install'.",
        "Ejecutar el build de producción con 'npm run build'.",
        "Crear un commit con los archivos del build.",
        "Hacer push a la rama 'release'.",
        "Generar informe final."
    ]
    ```

#### **Fase 2: La Capa de Comunicación (MCP Asíncrono)**

Implementaremos el sistema de colas basado en archivos que discutimos.

1.  **Formato del Mensaje (JSON):** Estandarizamos la comunicación.
    ```json
    {
        "id": "msg_1663882800",
        "timestamp": "2025-09-22T18:20:00Z",
        "source": "frontend-builder", // o "orchestrator"
        "type": "QUESTION", // STATUS_UPDATE, QUESTION, TASK_RESPONSE, COMMAND
        "payload": {
            "message": "Se requiere aprobación para hacer push. ¿Procedo?",
            "data": { "branch": "release" }
        }
    }
    ```

2.  **Gestor de Colas (`mcp/queue_manager.py`):**
    Funciones simples para leer y escribir en los archivos JSON de forma atómica, evitando corrupción de datos.

#### **Fase 3: El Cerebro del Agente (`core/agent.py`)**

Este es el corazón del AEA. Usaremos `asyncio` de Python para la concurrencia y no bloqueo.

1.  **El Bucle de Vida Asíncrono:**
    El agente tendrá un bucle principal `async def run()` que:
    a. Carga su configuración desde `agent_config.toml`.
    b. Inicia su estado (`state.py`) como `IDLE`.
    c. Comienza a "escuchar" en su cola de entrada (`orchestrator_queue`). Espera un mensaje `COMMAND` con `payload: {"action": "START"}`.
    d. Al recibir "START", cambia su estado a `RUNNING` y empieza a procesar las `tasks` de su plan, una por una.
    e. **Manejo de Tareas:** Para cada tarea, invoca a la herramienta correspondiente (Fase 4).
    f. **Comunicación Proactiva:** Después de cada tarea, envía un mensaje `STATUS_UPDATE` a su cola de salida (`agent_queue`).
    g. **Manejo de Esperas:** Si una tarea requiere una respuesta del orquestador, envía un `QUESTION`, cambia su estado a `AWAITING_RESPONSE` y se pone a escuchar en su cola de entrada hasta recibir la respuesta.

#### **Fase 4: Las Herramientas del Agente (`tools/`)**

Módulos con funciones específicas que el cerebro puede invocar. Todas deben ser `async`.

*   `tools/shell.py`: `async def run_command(command)` -> Ejecuta un comando en el `working_dir` del agente. Devuelve `stdout`, `stderr` y `exit_code`.
*   `tools/git.py`: `async def git_commit(message)`, `async def git_push(branch)` -> Usan `run_command` para interactuar con Git.
*   `tools/filesystem.py`: `async def create_report(content)` -> Para generar el informe final.

#### **Fase 5: Puesta en Marcha y Tareas a Realizar**

Ahora, unimos todo en una lista de tareas concretas para ti.

1.  **Tarea 1: Crear la Estructura.** Crea la estructura de directorios y archivos vacíos descrita en la Fase 1.
2.  **Tarea 2: Implementar el Gestor de Colas.** Desarrolla las funciones en `mcp/queue_manager.py`.
3.  **Tarea 3: Crear las Herramientas.** Implementa primero `tools/shell.py`, ya que las demás dependerán de ella. Luego `git.py` y `filesystem.py`.
4.  **Tarea 4: Desarrollar el Cerebro.** Implementa el bucle de vida y la lógica de estados en `core/agent.py` y `core/state.py`.
5.  **Tarea 5: Crear el Lanzador.** El `main.py` será muy simple: solo importará y ejecutará el `run()` del agente.
6.  **Tarea 6: Prueba de Concepto.** Rellena el `agent_config.toml` con un agente de prueba simple (ej. uno que solo liste archivos y cree un informe). Lánzalo y verifica que se comunica correctamente a través de los archivos de cola.
