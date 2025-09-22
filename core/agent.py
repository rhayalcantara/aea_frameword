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

    async def _process_task(self, task: Dict[str, Any]):
        """Procesa una única tarea estructurada del plan."""
        action = task.get('action')
        task_description = f"{action}: {task.get('filename', task.get('command', ''))}"
        await self._send_message("STATUS_UPDATE", {"message": f"Iniciando tarea: {task_description}"})
        
        try:
            details = ""
            if action == "run_command":
                command = task.get('command', '')
                result = await run_command(command, self.working_dir)
                if result["exit_code"] != 0:
                    raise Exception(f"Error al ejecutar comando: {result['stderr']}")
                details = result["stdout"]

            elif action == "write_file":
                content = task.get('content', '')
                filename = task.get('filename', '')
                filepath = os.path.join(self.working_dir, filename)
                result = await create_report(filepath, content) # create_report es nuestro write_file
                if result["status"] != "SUCCESS":
                    raise Exception(f"Error al escribir archivo: {result['message']}")
                details = f"Archivo {filename} creado exitosamente."
            
            elif action == "generate_and_write_code":
                server_url = task.get('server_url')
                output_file = os.path.join(self.working_dir, task.get('output_file'))
                
                await self._send_message("QUESTION", {
                    "message": f"Necesito que generes código para conectar a {server_url} y listar modelos.",
                    "request_type": "generate_code",
                    "server_url": server_url,
                    "output_file": output_file
                })
                self.state.set_status("AWAITING_RESPONSE")
                details = "Esperando código generado del orquestador."

            else:
                raise Exception(f"Acción de tarea no reconocida: {action}")

            if self.state.status != "AWAITING_RESPONSE": # No avanzar si estamos esperando respuesta
                await self._send_message("STATUS_UPDATE", {"message": f"Tarea completada: {task_description}", "details": details})
                self.state.add_history({"task": task_description, "result": details})
                self.state.next_task()

        except Exception as e:
            self.state.set_status("ERROR")
            await self._send_message("ERROR", {"message": f"Fallo en la tarea: {task_description}", "error": str(e)})


    async def run(self):
        """El bucle de vida principal del agente."""
        if not os.path.isdir(self.working_dir):
            os.makedirs(self.working_dir, exist_ok=True)
            await self._send_message("STATUS_UPDATE", {"message": f"Directorio de trabajo no existía. Creado: {self.working_dir}"})

        await self._send_message("STATUS_UPDATE", {"message": "Agente iniciado. Esperando comando START."})
        self.state.set_status("IDLE")

        while self.state.status not in ["FINISHED", "ERROR"]:
            messages = read_from_queue(self.comm_config['orchestrator_queue'])
            for msg in messages:
                if msg.get('type') == 'COMMAND' and msg['payload'].get('action') == 'START':
                    if self.state.status == 'IDLE':
                        self.state.set_status("RUNNING")
                        await self._send_message("STATUS_UPDATE", {"message": "Comando START recibido. Iniciando plan."})
                elif msg.get('type') == 'COMMAND' and msg['payload'].get('action') == 'CODE_GENERATED':
                    if self.state.status == 'AWAITING_RESPONSE':
                        generated_code = msg['payload']['code']
                        output_file = msg['payload']['output_file']
                        
                        # Escribir el código generado en el archivo
                        result = await create_report(output_file, generated_code)
                        if result["status"] != "SUCCESS":
                            await self._send_message("ERROR", {"message": f"Fallo al escribir el código generado en {output_file}", "error": result['message']})
                            self.state.set_status("ERROR")
                            break
                        
                        await self._send_message("STATUS_UPDATE", {"message": f"Código generado y escrito en {output_file}"})
                        self.state.add_history({"task": "generate_and_write_code", "result": f"Código escrito en {output_file}"})
                        self.state.next_task()
                        self.state.set_status("RUNNING") # Volver a RUNNING para continuar el plan

            # 2. Ejecutar el plan si el estado es RUNNING
            if self.state.status == "RUNNING":
                if self.state.current_task_index < len(self.plan['tasks']):
                    current_task = self.plan['tasks'][self.state.current_task_index]
                    await self._process_task(current_task)
                else:
                    self.state.set_status("FINISHED")
                    await self._send_message("STATUS_UPDATE", {"message": "Plan completado exitosamente."})

            # Espera antes de volver a sondear
            await asyncio.sleep(5)

        final_status = self.state.status
        await self._send_message("STATUS_UPDATE", {"message": f"Agente finalizado con estado: {final_status}"})
        print(f"Agente {self.state.name} ha finalizado.")