
import asyncio
import toml
import time
import json
from typing import Dict, Any, List

from core.state import AgentState
from mcp.queue_manager import read_from_queue, write_to_queue
from tools.shell import run_command
# Importaremos más herramientas a medida que las necesitemos

class Agent:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.state = AgentState(
            name=self.config['identity']['name'],
            role=self.config['identity']['role']
        )
        self.comm_config = self.config['communication']
        self.plan = self.config['plan']

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Carga la configuración desde un archivo TOML."""
        with open(config_path, 'r') as f:
            return toml.load(f)

    async def _send_message(self, msg_type: str, payload: Dict[str, Any]):
        """Envía un mensaje a la cola de salida del agente."""
        message = {
            "id": f"msg_{int(time.time())}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": self.state.name,
            "type": msg_type,
            "payload": payload
        }
        write_to_queue(self.comm_config['agent_queue'], message)

    async def _process_task(self, task: str):
        """Procesa una única tarea del plan."""
        await self._send_message("STATUS_UPDATE", {"message": f"Iniciando tarea: {task}"})
        
        # Lógica simple para mapear tarea a comando
        # Esto se puede hacer mucho más sofisticado
        try:
            if task.startswith("Ejecutar"): # Ej: "Ejecutar el build... con 'npm run build'."
                command = task.split("'")[1]
                result = await run_command(command, self.config['environment']['working_dir'])
                
                if result["exit_code"] != 0:
                    raise Exception(f"Error al ejecutar comando: {result['stderr']}")
                
                await self._send_message("STATUS_UPDATE", {"message": f"Tarea completada: {task}", "details": result["stdout"]})
                self.state.add_history({"task": task, "result": result})
            else:
                # Aquí iría la lógica para otras tareas (git, filesystem, etc.)
                await self._send_message("STATUS_UPDATE", {"message": f"Simulando tarea: {task}"})
                await asyncio.sleep(1) # Simula trabajo

            self.state.next_task()

        except Exception as e:
            self.state.set_status("ERROR")
            await self._send_message("ERROR", {"message": f"Fallo en la tarea: {task}", "error": str(e)})


    async def run(self):
        """El bucle de vida principal del agente."""
        await self._send_message("STATUS_UPDATE", {"message": "Agente iniciado. Esperando comando START."}) 
        self.state.set_status("IDLE")

        while self.state.status != "FINISHED" and self.state.status != "ERROR":
            # 1. Escuchar por comandos del orquestador
            messages = read_from_queue(self.comm_config['orchestrator_queue'])
            for msg in messages:
                if msg.get('type') == 'COMMAND' and msg['payload'].get('action') == 'START':
                    if self.state.status == 'IDLE':
                        self.state.set_status("RUNNING")
                        await self._send_message("STATUS_UPDATE", {"message": "Comando START recibido. Iniciando plan."})

            # 2. Ejecutar el plan si el estado es RUNNING
            if self.state.status == "RUNNING":
                if self.state.current_task_index < len(self.plan['tasks']):
                    current_task = self.plan['tasks'][self.state.current_task_index]
                    await self._process_task(current_task)
                else:
                    # Todas las tareas completadas
                    self.state.set_status("FINISHED")
                    await self._send_message("STATUS_UPDATE", {"message": "Plan completado exitosamente."})

            # Espera antes de volver a sondear
            await asyncio.sleep(5)

        final_status = self.state.status
        await self._send_message("STATUS_UPDATE", {"message": f"Agente finalizado con estado: {final_status}"})
        print(f"Agente {self.state.name} ha finalizado.")

