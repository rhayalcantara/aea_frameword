
from .shell import run_command
from typing import Dict, Any

async def git_commit(message: str, working_dir: str) -> Dict[str, Any]:
    """
    Realiza un git commit de forma asíncrona.
    Primero añade todos los cambios (git add .).
    """
    # Primero, añadir todos los cambios
    add_command = "git add ."
    add_result = await run_command(add_command, working_dir)
    if add_result["exit_code"] != 0:
        return add_result

    # Luego, hacer el commit
    commit_command = f'git commit -m "{message}"'
    return await run_command(commit_command, working_dir)

async def git_push(branch: str, working_dir: str) -> Dict[str, Any]:
    """
    Realiza un git push a una rama específica de forma asíncrona.
    """
    command = f"git push origin {branch}"
    return await run_command(command, working_dir)
