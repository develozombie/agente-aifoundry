"""
DESCRIPCIÓN:
    Esta muestra demuestra un agente conversacional usando
    el servicio Azure Agents con entrada del usuario y selección de agente.

USO:
    python conversar_agente.py

    Antes de ejecutar la muestra:

    pip install azure-ai-agents azure-identity

    Configura estas variables de entorno con tus propios valores:
    1) PROJECT_ENDPOINT - el endpoint de Azure AI Agents.
    2) MODEL_DEPLOYMENT_NAME - El nombre de despliegue del modelo de IA, como se encuentra bajo la columna "Nombre" en 
       la pestaña "Modelos + endpoints" en tu proyecto Azure AI Foundry.
"""

import os, time, sys, json
from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder, MessageTextContent
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions
from dotenv import load_dotenv

# Importaciones para tracing
from azure.ai.inference.tracing import AIInferenceInstrumentor
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Configurar encoding UTF-8 para manejo de caracteres especiales
if sys.platform.startswith('win'):
    # Windows: configurar encoding UTF-8
    import locale
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
else:
    # Unix/Linux/macOS: asegurar encoding UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'

load_dotenv(encoding='utf-8')

# Cargar info de sesion de usuario
metadata_usuario = {
            "customer_id": "88129215"
}
# Configurar instrumentación de tracing
AIInferenceInstrumentor().instrument()

# Configurar Azure Monitor si APPLICATION_INSIGHTS_CONNECTION_STRING está disponible
if "APPLICATION_INSIGHTS_CONNECTION_STRING" in os.environ:
    configure_azure_monitor(
        connection_string=os.environ["APPLICATION_INSIGHTS_CONNECTION_STRING"]
    )
    print("✅ Tracing de Azure Monitor configurado")
else:
    print("ℹ️ APPLICATION_INSIGHTS_CONNECTION_STRING no configurado, usando tracing local")

# Obtener el trazador
trazador = trace.get_tracer(__name__)

# [INICIO crear_cliente_proyecto]
cliente_agentes = AgentsClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

# Cliente de Seguridad de Contenido - usar endpoint separado si está disponible, de lo contrario omitir moderación
cliente_seguridad_contenido = None
try:
    if "CONTENT_SAFETY_ENDPOINT" in os.environ:
        cliente_seguridad_contenido = ContentSafetyClient(
            endpoint=os.environ["CONTENT_SAFETY_ENDPOINT"],
            credential=DefaultAzureCredential(),
        )
    else:
        print("Nota: CONTENT_SAFETY_ENDPOINT no configurado, moderación de contenido deshabilitada")
except Exception as e:
    print(f"Advertencia: No se pudo inicializar el cliente de Seguridad de Contenido: {e}")
    cliente_seguridad_contenido = None
# [FIN crear_cliente_proyecto]

def moderar_texto(texto, cliente):
    """Moderar contenido de texto usando Azure AI Content Safety"""
    with trazador.start_as_current_span("moderar_texto") as span:
        span.set_attribute("input.text_length", len(texto))
        
        if cliente is None:
            span.set_attribute("moderation.enabled", False)
            return True, "Moderación de contenido deshabilitada", None
            
        try:
            span.set_attribute("moderation.enabled", True)
            solicitud = AnalyzeTextOptions(text=texto)
            respuesta = cliente.analyze_text(solicitud)
            
            # Verificar si el contenido es seguro (puedes ajustar estos umbrales)
            esta_marcado = False
            categorias_marcadas = []
            severidad_maxima = 0
            
            for resultado_categoria in respuesta.categories_analysis:
                severidad_maxima = max(severidad_maxima, resultado_categoria.severity)
                span.set_attribute(f"moderation.{resultado_categoria.category.lower()}_severity", resultado_categoria.severity)
                
                if resultado_categoria.severity >= 2:  # Severidad media
                    esta_marcado = True
                    categorias_marcadas.append(f"{resultado_categoria.category} (severidad: {resultado_categoria.severity})")
            
            span.set_attribute("moderation.max_severity", severidad_maxima)
            span.set_attribute("moderation.is_flagged", esta_marcado)
            
            if esta_marcado:
                span.set_status(Status(StatusCode.ERROR, "Contenido marcado por políticas de seguridad"))
                return False, f"Contenido marcado por: {', '.join(categorias_marcadas)}", respuesta
            else:
                span.set_status(Status(StatusCode.OK))
                return True, "El contenido es seguro", respuesta
                
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            print(f"Advertencia: La moderación de contenido falló: {e}")
            return True, "Moderación no disponible", None

def imprimir_resultados_seguridad_contenido(respuesta):
    """Imprimir resultados detallados del análisis de Seguridad de Contenido"""
    if respuesta is None:
        print("📊 Seguridad de Contenido: Análisis no disponible")
        return
    
    print("📊 Análisis de Seguridad de Contenido:")
    for resultado_categoria in respuesta.categories_analysis:
        emoji_severidad = "🟢" if resultado_categoria.severity <= 1 else "🟡" if resultado_categoria.severity <= 3 else "🔴"
        print(f"   {emoji_severidad} {resultado_categoria.category}: Severidad {resultado_categoria.severity}")
    print()

def obtener_entrada_usuario_segura():
    """
    Obtiene entrada del usuario con manejo robusto de encoding UTF-8.
    
    @returns {str} Entrada del usuario limpia y decodificada correctamente
    @raises {UnicodeDecodeError} Manejado internamente, retorna string vacío en caso de error
    """
    try:
        # Intentar obtener entrada con encoding UTF-8
        entrada = input("Tú: ")
        # Asegurar que la entrada sea una cadena UTF-8 válida
        if isinstance(entrada, bytes):
            entrada = entrada.decode('utf-8', errors='replace')
        return entrada.strip()
    except UnicodeDecodeError as e:
        print(f"⚠️ Error de codificación detectado: {e}")
        print("💡 Intenta usar solo caracteres ASCII o UTF-8 válidos.")
        return ""
    except EOFError:
        # Manejar Ctrl+D en Unix o Ctrl+Z en Windows
        print("\n👋 Sesión terminada por el usuario.")
        return "salir"
    except KeyboardInterrupt:
        # Manejar Ctrl+C
        print("\n👋 Sesión interrumpida por el usuario.")
        return "salir"
    except Exception as e:
        print(f"⚠️ Error inesperado al leer entrada: {e}")
        return ""

def obtener_agentes_disponibles():
    """
    Obtiene la lista de agentes disponibles desde variables de entorno.
    
    @returns {list} Lista de agentes con su información
    """
    try:
        agentes_json = os.environ.get("AGENTS_DATA", "[]")
        agentes = json.loads(agentes_json)
        return agentes
    except json.JSONDecodeError:
        return []
    except Exception as e:
        print(f"⚠️ Error al obtener agentes: {e}")
        return []

def seleccionar_agente():
    """
    Permite al usuario seleccionar un agente para la conversación.
    
    @returns {str} ID del agente seleccionado
    """
    agentes = obtener_agentes_disponibles()
    
    if not agentes:
        print("📭 No hay agentes disponibles")
        print("💡 Ejecuta primero: python crear_agente.py")
        sys.exit(1)
    
    print("\n🤖 Selecciona un agente para conversar:")
    print("=" * 50)
    
    # Mostrar agentes disponibles
    for i, agente in enumerate(agentes, 1):
        print(f"{i}. {agente['nombre']} ({agente['tipo']})")
        print(f"   ID: {agente['id']}")
        print(f"   Creado: {agente.get('fecha_creacion', 'N/A')}")
        print()
    
    print(f"{len(agentes) + 1}. Ingresar ID manualmente")
    print("0. Salir")
    
    while True:
        try:
            opcion = input("\nIngresa tu opción: ").strip()
            
            if opcion == "0":
                print("👋 ¡Hasta luego!")
                sys.exit(0)
            elif opcion == str(len(agentes) + 1):
                # Ingresar ID manualmente
                agent_id = input("\n🆔 Ingresa el ID del agente: ").strip()
                if agent_id:
                    # Validar que el agente existe
                    try:
                        with AgentsClient(
                            endpoint=os.environ["PROJECT_ENDPOINT"],
                            credential=DefaultAzureCredential(),
                        ) as cliente:
                            agente = cliente.get_agent(agent_id)
                            print(f"✅ Agente encontrado: {agente.name}")
                            return agent_id
                    except Exception as e:
                        print(f"❌ Error al validar agente {agent_id}: {e}")
                        continue
                else:
                    print("❌ ID no válido")
                    continue
            else:
                try:
                    indice = int(opcion) - 1
                    if 0 <= indice < len(agentes):
                        agente_seleccionado = agentes[indice]
                        print(f"✅ Seleccionaste: {agente_seleccionado['nombre']}")
                        return agente_seleccionado['id']
                    else:
                        print("❌ Opción no válida")
                        continue
                except ValueError:
                    print("❌ Por favor ingresa un número válido")
                    continue
                    
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            sys.exit(0)

with cliente_agentes:
    with trazador.start_as_current_span("sesion_agente_conversacional") as span_sesion:
        # Seleccionar agente
        agent_id = seleccionar_agente()
        
        try:
            # Obtener agente existente
            agente = cliente_agentes.get_agent(agent_id)
            print(f"\n✅ Usando agente: {agente.name}")
            print(f"🆔 ID del agente: {agente.id}")
        except Exception as e:
            print(f"❌ Error al obtener agente {agent_id}: {e}")
            print("💡 El agente puede haber sido eliminado. Ejecuta: python crear_agente.py")
            sys.exit(1)

        # [INICIO crear_hilo]
        hilo = cliente_agentes.threads.create()
        # [FIN crear_hilo]
        print(f"🧵 Hilo creado, ID del hilo: {hilo.id}")
        print("¡Agente Conversacional Listo! Escribe 'salir' o 'quit' para terminar la conversación.\n")

        span_sesion.set_attribute("agent.id", agente.id)
        span_sesion.set_attribute("thread.id", hilo.id)
        span_sesion.set_attribute("agent.name", agente.name)
        
        contador_conversacion = 0
        
        # [INICIO bucle_conversacion]
        while True:
            with trazador.start_as_current_span("intercambio_conversacional") as span_intercambio:
                contador_conversacion += 1
                span_intercambio.set_attribute("conversation.turn", contador_conversacion)
                
                # Obtener entrada del usuario con manejo seguro de encoding
                entrada_usuario = obtener_entrada_usuario_segura()
                span_intercambio.set_attribute("user.input", entrada_usuario)
                span_intercambio.set_attribute("user.input_length", len(entrada_usuario))
                
                # Verificar comandos de salida
                if entrada_usuario.lower() in ['quit', 'exit', 'bye', 'salir', 'adiós']:
                    print("Agente: ¡Adiós! ¡Que tengas un gran día!")
                    span_intercambio.set_attribute("conversation.ended", True)
                    break
                    
                if not entrada_usuario:
                    span_intercambio.set_attribute("user.input_empty", True)
                    continue

                # Moderar entrada del usuario
                with trazador.start_as_current_span("moderacion_entrada_usuario"):
                    es_seguro, resultado_moderacion, respuesta_seguridad = moderar_texto(entrada_usuario, cliente_seguridad_contenido)
                
                # Mostrar análisis de Seguridad de Contenido
                imprimir_resultados_seguridad_contenido(respuesta_seguridad)
                
                if not es_seguro:
                    span_intercambio.set_attribute("user.input_blocked", True)
                    span_intercambio.set_attribute("block_reason", resultado_moderacion)
                    print(f"Agente: No puedo responder a ese mensaje. {resultado_moderacion}")
                    print()
                    continue

                span_intercambio.set_attribute("user.input_safe", True)

                # Crear mensaje del usuario
                with trazador.start_as_current_span("crear_mensaje_usuario"):
                    mensaje = cliente_agentes.messages.create(
                        thread_id=hilo.id, 
                        role="user", 
                        content=f"[CONTEXT: customer_id={metadata_usuario['customer_id']}] {entrada_usuario}"
                    )

                # Crear y ejecutar el agente
                with trazador.start_as_current_span("ejecutar_agente") as span_ejecucion:
                    ejecucion = cliente_agentes.runs.create(thread_id=hilo.id, agent_id=agente.id)
                    span_ejecucion.set_attribute("run.id", ejecucion.id)
                    
                    tiempo_inicio = time.time()
                    
                    # Sondear hasta que la ejecución esté completa
                    while ejecucion.status in ["queued", "in_progress", "requires_action"]:
                        time.sleep(1)
                        ejecucion = cliente_agentes.runs.get(thread_id=hilo.id, run_id=ejecucion.id)
                    
                    tiempo_fin = time.time()
                    duracion_ejecucion = tiempo_fin - tiempo_inicio
                    
                    span_ejecucion.set_attribute("run.status", str(ejecucion.status))
                    span_ejecucion.set_attribute("run.duration_seconds", duracion_ejecucion)

                # Obtener los mensajes más recientes
                with trazador.start_as_current_span("obtener_respuesta_agente") as span_respuesta:
                    mensajes = cliente_agentes.messages.list(thread_id=hilo.id, order=ListSortOrder.DESCENDING)

                    # Encontrar y mostrar la respuesta del agente
                    for mensaje in mensajes:
                        if mensaje.role == "assistant":
                            if hasattr(mensaje, 'content') and mensaje.content:
                                for elemento_contenido in mensaje.content:
                                    if isinstance(elemento_contenido, MessageTextContent):
                                        respuesta_agente = elemento_contenido.text.value
                                        
                                        span_respuesta.set_attribute("agent.response", respuesta_agente)
                                        span_respuesta.set_attribute("agent.response_length", len(respuesta_agente))
                                        
                                        # Moderar respuesta del agente
                                        with trazador.start_as_current_span("moderacion_respuesta_agente"):
                                            es_respuesta_segura, moderacion_respuesta, respuesta_seguridad_agente = moderar_texto(respuesta_agente, cliente_seguridad_contenido)
                                        
                                        if es_respuesta_segura:
                                            span_respuesta.set_attribute("agent.response_safe", True)
                                            print(f"Agente: {respuesta_agente}")
                                            # Mostrar análisis de seguridad de la respuesta del agente
                                            if respuesta_seguridad_agente:
                                                print("📊 Análisis de Seguridad de Respuesta del Agente:")
                                                for resultado_categoria in respuesta_seguridad_agente.categories_analysis:
                                                    emoji_severidad = "🟢" if resultado_categoria.severity <= 1 else "🟡" if resultado_categoria.severity <= 3 else "🔴"
                                                    print(f"   {emoji_severidad} {resultado_categoria.category}: Severidad {resultado_categoria.severity}")
                                        else:
                                            span_respuesta.set_attribute("agent.response_blocked", True)
                                            span_respuesta.set_attribute("agent.block_reason", moderacion_respuesta)
                                            print("Agente: Me disculpo, pero no puedo proporcionar esa respuesta debido a la política de contenido.")
                                            imprimir_resultados_seguridad_contenido(respuesta_seguridad_agente)
                            break
                
                print()  # Agregar espaciado entre intercambios
        # [FIN bucle_conversacion]
        
        span_sesion.set_attribute("conversation.total_turns", contador_conversacion)
    
    # Ya no eliminamos el agente - se mantiene para futuras sesiones
    print("✅ Sesión de conversación completada")
    print("💡 El agente se mantiene activo para futuras conversaciones")
