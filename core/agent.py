
import asyncio
import toml
import time
import json
import os
from typing import Dict, Any, List

from core.state import AgentState
from mcp.queue_manager import read_from_queue, write_to_queue
from tools.shell import run_command
from tools.filesystem import create_report

class Agent:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.state = AgentState(
            name=self.config['identity']['name'],
            role=self.config['identity']['role']
        )
        self.comm_config = self.config['communication']
        self.plan = self.config['plan']
        self.working_dir = self.config['environment']['working_dir']

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
        await self._send_message("STATUS_UPDATE", {"message": f"Iniciando tarea: {task[:80]}..."})
        
        try:
            if task.startswith("Ejecutar"):
                command = task.split("'")[1]
                result = await run_command(command, self.working_dir)
                if result["exit_code"] != 0:
                    raise Exception(f"Error al ejecutar comando: {result['stderr']}")
                details = result["stdout"]

            elif task.startswith("Crear el archivo"):
                parts = task.split("'''")
                content = parts[1].strip()
                filename = task.split("'")[1]
                filepath = os.path.join(self.working_dir, filename)
                # Usaremos create_report que funciona como un generic write_file
                result = await create_report(filepath, content)
                if result["status"] != "SUCCESS":
                    raise Exception(f"Error al escribir archivo: {result['message']}")
                details = f"Archivo {filename} creado exitosamente."
            
            else:
                # Tarea no reconocida, la simulamos
                details = f"Simulando tarea no reconocida: {task[:80]}..."
                await asyncio.sleep(1)

            await self._send_message("STATUS_UPDATE", {"message": f"Tarea completada: {task[:80]}...", "details": details})
            self.state.add_history({"task": task, "result": details})
            self.state.next_task()

        except Exception as e:
            self.state.set_status("ERROR")
            await self._send_message("ERROR", {"message": f"Fallo en la tarea: {task[:80]}...", "error": str(e)})


    async def run(self):
        """El bucle de vida principal del agente."""
        # Asegurarse que el directorio de trabajo exista
        if not os.path.isdir(self.working_dir):
            await self._send_message("ERROR", {"message": f"El directorio de trabajo no existe: {self.working_dir}"})
            self.state.set_status("ERROR")
            print(f"Agente {self.state.name} ha finalizado con error.")
            return

        await self._send_message("STATUS_UPDATE", {"message": "Agente iniciado. Esperando comando START."})
        self.state.set_status("IDLE")

        while self.state.status not in ["FINISHED", "ERROR"]:
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

