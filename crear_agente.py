"""
DESCRIPCIÓN:
    Módulo para crear y gestionar agentes de Azure AI Agents.
    Crea un agente y guarda su ID en variables de entorno para reutilización.

USO:
    python crear_agente.py

FUNCIONALIDADES:
    - Creación de agentes con configuración personalizada
    - Persistencia del ID del agente en archivo .env
    - Validación de configuración existente
    - Limpieza de agentes obsoletos
"""

import os
import sys
from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv, set_key
from opentelemetry import trace
from azure.ai.inference.tracing import AIInferenceInstrumentor

# Configurar encoding UTF-8
if sys.platform.startswith('win'):
    import locale
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
else:
    os.environ['PYTHONIOENCODING'] = 'utf-8'

load_dotenv(encoding='utf-8')

# Configurar instrumentación
AIInferenceInstrumentor().instrument()
trazador = trace.get_tracer(__name__)

class GestorAgente:
    """
    Gestor para crear, configurar y mantener agentes de Azure AI.
    
    @class GestorAgente
    @description Maneja el ciclo de vida completo de agentes conversacionales
    """
    
    def __init__(self):
        """
        Inicializa el gestor de agentes con cliente configurado.
        """
        self.cliente = AgentsClient(
            endpoint=os.environ["PROJECT_ENDPOINT"],
            credential=DefaultAzureCredential(),
        )
        self.archivo_env = ".env"
    
    def crear_agente(self, nombre="Mobilito", instrucciones=None):
        """
        Crea un nuevo agente y guarda su ID en variables de entorno.
        
        @param {str} nombre - Nombre del agente
        @param {str} instrucciones - Instrucciones del sistema para el agente
        @returns {str} ID del agente creado
        """
        with trazador.start_as_current_span("crear_agente_nuevo") as span:
            try:
                if instrucciones is None:
                    instrucciones = """Eres Mobilito, un asistente conversacional especializado en ayudar con consultas bancarias y financieras. 
                    Sé amigable, profesional y proporciona respuestas útiles y precisas. 
                    Siempre mantén la confidencialidad y seguridad en todas las interacciones."""
                
                span.set_attribute("agent.name", nombre)
                span.set_attribute("agent.instructions_length", len(instrucciones))
                
                agente = self.cliente.create_agent(
                    model=os.environ["MODEL_DEPLOYMENT_NAME"],
                    name=nombre,
                    instructions=instrucciones,
                )
                
                # Guardar ID del agente en archivo .env
                self.guardar_id_agente(agente.id)
                
                span.set_attribute("agent.id", agente.id)
                span.set_attribute("agent.created", True)
                
                print(f"✅ Agente '{nombre}' creado exitosamente")
                print(f"🆔 ID del agente: {agente.id}")
                print(f"💾 ID guardado en {self.archivo_env}")
                
                return agente.id
                
            except Exception as e:
                span.record_exception(e)
                print(f"❌ Error al crear agente: {e}")
                raise
    
    def guardar_id_agente(self, agent_id):
        """
        Guarda el ID del agente en el archivo .env.
        
        @param {str} agent_id - ID del agente a guardar
        """
        try:
            # Actualizar archivo .env con el nuevo ID
            set_key(self.archivo_env, "AGENT_ID", agent_id)
            print(f"💾 ID del agente guardado: AGENT_ID={agent_id}")
        except Exception as e:
            print(f"⚠️ Error al guardar ID del agente: {e}")
    
    def obtener_agente_existente(self):
        """
        Obtiene información del agente existente desde variables de entorno.
        
        @returns {str|None} ID del agente existente o None si no existe
        """
        agent_id = os.environ.get("AGENT_ID")
        if agent_id:
            try:
                # Verificar que el agente aún existe en el servicio
                with self.cliente as cliente:
                    agente = cliente.get_agent(agent_id)
                    print(f"✅ Agente existente encontrado: {agente.name} ({agent_id})")
                    return agent_id
            except Exception as e:
                print(f"⚠️ Agente con ID {agent_id} no encontrado o inaccesible: {e}")
                return None
        return None
    
    def limpiar_agente(self, agent_id):
        """
        Elimina un agente del servicio.
        
        @param {str} agent_id - ID del agente a eliminar
        """
        try:
            with self.cliente as cliente:
                cliente.delete_agent(agent_id)
                print(f"🗑️ Agente {agent_id} eliminado del servicio")
        except Exception as e:
            print(f"⚠️ Error al eliminar agente {agent_id}: {e}")

def main():
    """
    Función principal para crear o verificar agente.
    """
    print("🤖 Gestor de Agentes Azure AI")
    print("=" * 40)
    
    gestor = GestorAgente()
    
    # Verificar si ya existe un agente
    agent_id_existente = gestor.obtener_agente_existente()
    
    if agent_id_existente:
        respuesta = input("¿Deseas crear un nuevo agente? (s/N): ").strip().lower()
        if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
            # Limpiar agente anterior
            gestor.limpiar_agente(agent_id_existente)
            # Crear nuevo agente
            gestor.crear_agente()
        else:
            print(f"✅ Usando agente existente: {agent_id_existente}")
    else:
        # Crear nuevo agente
        gestor.crear_agente()
    
    print("\n🎉 Configuración de agente completada!")
    print("💡 Ahora puedes ejecutar: python basic-agent.py")

if __name__ == "__main__":
    main()
