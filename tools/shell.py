
import asyncio
from typing import Dict, Any

async def run_command(command: str, working_dir: str) -> Dict[str, Any]:
    """
    Ejecuta un comando de shell de forma asíncrona en un directorio de trabajo específico.

    Args:
        command: El comando a ejecutar.
        working_dir: El directorio donde se ejecutará el comando.

    Returns:
        Un diccionario con stdout, stderr, y el código de salida.
    """
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=working_dir
    )

    stdout, stderr = await process.communicate()

    return {
        "stdout": stdout.decode().strip(),
        "stderr": stderr.decode().strip(),
        "exit_code": process.returncode
    }

