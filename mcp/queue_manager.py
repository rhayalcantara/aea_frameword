import json
import fcntl
from typing import List, Dict, Any

def write_to_queue(queue_path: str, message: Dict[str, Any]) -> None:
    """
    Añade un mensaje a la cola (archivo JSON) de forma segura.
    Lee la lista actual, añade el nuevo mensaje y la escribe de nuevo.
    """
    try:
        # Intentamos abrir en modo r+ para leer y luego escribir
        with open(queue_path, 'r+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                messages = json.load(f)
            except json.JSONDecodeError:
                messages = []
            
            messages.append(message)
            
            f.seek(0)
            f.truncate()
            json.dump(messages, f, indent=4)
            fcntl.flock(f, fcntl.LOCK_UN)

    except FileNotFoundError:
        # Si el archivo no existe, lo crea con el primer mensaje
        with open(queue_path, 'w') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump([message], f, indent=4)
            fcntl.flock(f, fcntl.LOCK_UN)
    except IOError as e:
        print(f"Error al escribir en la cola {queue_path}: {e}")

def read_from_queue(queue_path: str) -> List[Dict[str, Any]]:
    """
    Lee todos los mensajes de la cola y la vacía de forma segura.
    """
    messages = []
    try:
        with open(queue_path, 'r+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                messages = json.load(f)
            except json.JSONDecodeError:
                # La cola está vacía o corrupta, se considera vacía
                messages = []

            # Vaciar el archivo después de leer
            f.seek(0)
            f.truncate()
            json.dump([], f, indent=4) # Escribe una lista JSON vacía
            fcntl.flock(f, fcntl.LOCK_UN)

    except FileNotFoundError:
        # Si el archivo no existe, lo creamos con una lista vacía
        with open(queue_path, 'w') as f:
            json.dump([], f, indent=4)

    except IOError as e:
        print(f"Error al leer de la cola {queue_path}: {e}")
    
    return messages