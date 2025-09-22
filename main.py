
import asyncio
from core.agent import Agent

CONFIG_FILE = 'agent_config.toml'

async def main():
    """
    Punto de entrada principal para lanzar el Agente Especializado Asíncrono.
    """
    print(f"Iniciando agente desde la configuración: {CONFIG_FILE}")
    agent = Agent(config_path=CONFIG_FILE)
    await agent.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAgente detenido por el usuario.")

