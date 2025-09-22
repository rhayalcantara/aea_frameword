
import os
from typing import Dict, Any

async def create_report(report_path: str, content: str) -> Dict[str, Any]:
    """
    Crea un archivo de informe.

    Args:
        report_path: La ruta completa donde se guardará el informe.
        content: El contenido del informe.

    Returns:
        Un diccionario indicando el éxito o fracaso de la operación.
    """
    try:
        with open(report_path, 'w') as f:
            f.write(content)
        return {"status": "SUCCESS", "path": report_path}
    except IOError as e:
        return {"status": "ERROR", "message": str(e)}

