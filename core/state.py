
from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal

AgentStatus = Literal["IDLE", "RUNNING", "AWAITING_RESPONSE", "FINISHED", "ERROR"]

@dataclass
class AgentState:
    """Almacena y gestiona el estado interno de un agente."""
    name: str
    role: str
    status: AgentStatus = "IDLE"
    current_task_index: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)

    def add_history(self, entry: Dict[str, Any]):
        """Añade una entrada al historial de acciones del agente."""
        self.history.append(entry)

    def next_task(self):
        """Avanza al siguiente índice de tarea."""
        self.current_task_index += 1

    def set_status(self, status: AgentStatus):
        """Actualiza el estado del agente."""
        self.status = status
