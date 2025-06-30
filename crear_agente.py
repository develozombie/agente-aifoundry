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
import json
from azure.ai.agents import AgentsClient  
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv, set_key
from opentelemetry import trace
from azure.ai.inference.tracing import AIInferenceInstrumentor
import importlib

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
        Inicializa el gestor de agentes con configuración de cliente.
        """
        self.endpoint = os.environ["PROJECT_ENDPOINT"]
        self.credential = DefaultAzureCredential()
        self.archivo_env = ".env"
    
    def _get_client(self):
        """
        Crea y retorna un nuevo cliente de agentes.
        
        @returns {AgentsClient} Cliente configurado
        """
        return AgentsClient(
            endpoint=self.endpoint,
            credential=self.credential,
        )
    
    def crear_agente(self, nombre=None, instrucciones=None, tipo_agente=None):
        """
        Crea un nuevo agente y guarda su información en variables de entorno.
        
        @param {str} nombre - Nombre del agente (opcional)
        @param {str} instrucciones - Instrucciones del sistema para el agente (opcional)
        @param {str} tipo_agente - Tipo de agente: 'basico', 'mcp', 'azure_function' (opcional)
        @returns {str} ID del agente creado
        """
        with trazador.start_as_current_span("crear_agente_nuevo") as span:
            try:
                # Solicitar nombre (obligatorio)
                nombre = self._obtener_nombre_agente(nombre)
                if not nombre:
                    print("❌ El nombre del agente es obligatorio")
                    return None
                
                # Solicitar instrucciones (obligatorio)
                instrucciones = self._obtener_instrucciones_agente(instrucciones)
                if not instrucciones:
                    print("❌ Las instrucciones del agente son obligatorias")
                    return None
                
                # Si no se especifica tipo, preguntar al usuario
                if tipo_agente is None:
                    tipo_agente = self._obtener_tipo_agente()
                
                # Validar que el nombre no esté duplicado
                agentes_existentes = self.obtener_agentes_existentes()
                if any(agente['nombre'] == nombre for agente in agentes_existentes):
                    respuesta = input(f"⚠️ Ya existe un agente con el nombre '{nombre}'. ¿Crear con nombre diferente? (s/N): ").strip().lower()
                    if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
                        contador = 1
                        nombre_original = nombre
                        while any(agente['nombre'] == nombre for agente in agentes_existentes):
                            nombre = f"{nombre_original}_{contador}"
                            contador += 1
                        print(f"✅ Usando nombre: {nombre}")
                    else:
                        print("❌ Cancelado por el usuario")
                        return None
                
                span.set_attribute("agent.name", nombre)
                span.set_attribute("agent.type", tipo_agente)
                span.set_attribute("agent.instructions_length", len(instrucciones))
                
                print(f"\n🔧 Creando agente de tipo: {tipo_agente}")
                print(f"📋 Nombre: {nombre}")
                print(f"📝 Instrucciones: {instrucciones[:100]}..." if len(instrucciones) > 100 else f"📝 Instrucciones: {instrucciones}")
                
                # Confirmar creación
                confirmacion = input("\n¿Proceder con la creación del agente? (S/n): ").strip().lower()
                if confirmacion in ['n', 'no']:
                    print("❌ Creación cancelada")
                    return None
                
                # Crear agente según el tipo seleccionado
                if tipo_agente == "basico":
                    agente = self._crear_agente_basico(nombre, instrucciones)
                elif tipo_agente == "mcp":
                    agente = self._crear_agente_mcp(nombre, instrucciones)
                elif tipo_agente == "azure_function":
                    agente = self._crear_agente_azure_function(nombre, instrucciones)
                else:
                    raise ValueError(f"Tipo de agente no válido: {tipo_agente}")
                
                # Guardar información del agente
                self.guardar_agente(agente.id, nombre, tipo_agente, instrucciones)
                
                span.set_attribute("agent.id", agente.id)
                span.set_attribute("agent.created", True)
                
                print(f"✅ Agente '{nombre}' ({tipo_agente}) creado exitosamente")
                print(f"🆔 ID del agente: {agente.id}")
                print(f"💾 Información guardada en {self.archivo_env}")
                
                return agente.id
                
            except Exception as e:
                span.record_exception(e)
                print(f"❌ Error al crear agente: {e}")
                raise

    def _obtener_nombre_agente(self, nombre_sugerido=None):
        """
        Solicita al usuario que configure el nombre del agente.
        
        @param {str} nombre_sugerido - Nombre sugerido (opcional)
        @returns {str} Nombre del agente configurado por el usuario
        """
        print("\n📝 Configuración del nombre del agente:")
        print("=" * 50)
        
        while True:
            try:
                if nombre_sugerido:
                    nombre = input(f"📝 Nombre del agente (sugerido: '{nombre_sugerido}'): ").strip()
                    if not nombre:
                        nombre = nombre_sugerido
                else:
                    nombre = input("📝 Nombre del agente (obligatorio): ").strip()
                
                if nombre:
                    # Validar que el nombre no contenga caracteres especiales problemáticos
                    if self._validar_nombre_agente(nombre):
                        return nombre
                    else:
                        print("❌ El nombre contiene caracteres no válidos. Usa solo letras, números, espacios y guiones.")
                        continue
                else:
                    print("❌ El nombre del agente es obligatorio. Por favor ingresa un nombre.")
                    continue
                    
            except KeyboardInterrupt:
                print("\n❌ Operación cancelada por el usuario")
                return None

    def _validar_nombre_agente(self, nombre):
        """
        Valida que el nombre del agente sea válido.
        
        @param {str} nombre - Nombre a validar
        @returns {bool} True si el nombre es válido
        """
        import re
        # Permitir letras, números, espacios, guiones y guiones bajos
        patron = r'^[a-zA-Z0-9\s\-_ñÑáéíóúÁÉÍÓÚüÜ]+$'
        return bool(re.match(patron, nombre)) and len(nombre.strip()) > 0

    def _obtener_instrucciones_agente(self, instrucciones_sugeridas=None):
        """
        Solicita al usuario que configure las instrucciones del agente.
        
        @param {str} instrucciones_sugeridas - Instrucciones sugeridas (opcional)
        @returns {str} Instrucciones personalizadas del agente
        """
        print("\n📝 Configuración de instrucciones del agente:")
        print("=" * 50)
        print("💡 Las instrucciones definen el comportamiento y personalidad del agente.")
        print("💡 Ejemplo: 'Eres un asistente especializado en atención al cliente...'")
        
        if instrucciones_sugeridas:
            print(f"\nInstrucciones sugeridas:")
            print(f"'{instrucciones_sugeridas}'")
            print("=" * 50)
        
        opciones = []
        if instrucciones_sugeridas:
            opciones.extend([
                "1. Usar instrucciones sugeridas",
                "2. Escribir instrucciones personalizadas",
                "3. Modificar las instrucciones sugeridas"
            ])
        else:
            opciones.extend([
                "1. Escribir instrucciones personalizadas",
                "2. Obtener ejemplos de instrucciones"
            ])
        
        for opcion in opciones:
            print(opcion)
        
        while True:
            try:
                if instrucciones_sugeridas:
                    eleccion = input("\nSelecciona una opción (1-3): ").strip()
                    
                    if eleccion == "1":
                        return instrucciones_sugeridas
                    elif eleccion == "2":
                        return self._escribir_instrucciones_personalizadas()
                    elif eleccion == "3":
                        return self._modificar_instrucciones_por_defecto(instrucciones_sugeridas)
                    else:
                        print("❌ Opción no válida. Por favor ingresa 1, 2 o 3.")
                else:
                    eleccion = input("\nSelecciona una opción (1-2): ").strip()
                    
                    if eleccion == "1":
                        return self._escribir_instrucciones_personalizadas()
                    elif eleccion == "2":
                        self._mostrar_ejemplos_instrucciones()
                        continue
                    else:
                        print("❌ Opción no válida. Por favor ingresa 1 o 2.")
                        
            except KeyboardInterrupt:
                print("\n❌ Operación cancelada por el usuario")
                return None

    def _mostrar_ejemplos_instrucciones(self):
        """
        Muestra ejemplos de instrucciones para diferentes tipos de agentes.
        """
        print("\n📚 Ejemplos de instrucciones por tipo de agente:")
        print("=" * 60)
        
        ejemplos = {
            "Asistente de Atención al Cliente": """Eres un asistente de atención al cliente especializado en resolver consultas de manera amigable y profesional. 
Siempre saluda cordialmente, escucha activamente las necesidades del cliente y proporciona soluciones claras y precisas. 
Mantén un tono empático y profesional en todas las interacciones.""",
            
            "Asistente Técnico": """Eres un asistente técnico especializado en resolver problemas de software y hardware. 
Proporciona instrucciones paso a paso claras y comprensibles. 
Siempre pregunta por detalles específicos cuando sea necesario y ofrece múltiples soluciones cuando sea posible.""",
            
            "Asistente de Ventas": """Eres un asistente de ventas especializado en ayudar a los clientes a encontrar los productos que mejor se adapten a sus necesidades. 
Haz preguntas relevantes para entender los requisitos del cliente y recomienda productos de manera honesta y transparente. 
Siempre destaca los beneficios y características más importantes.""",
            
            "Asistente Educativo": """Eres un asistente educativo que ayuda a los estudiantes a aprender de manera efectiva. 
Explica conceptos complejos de manera simple y usa ejemplos prácticos. 
Sé paciente, alentador y adapta tu estilo de enseñanza al nivel del estudiante."""
        }
        
        for i, (tipo, ejemplo) in enumerate(ejemplos.items(), 1):
            print(f"\n{i}. {tipo}:")
            print(f"   {ejemplo}")
        
        print("\n💡 Usa estos ejemplos como inspiración para crear tus propias instrucciones.")
        input("\nPresiona Enter para continuar...")

    def _escribir_instrucciones_personalizadas(self):
        """
        Permite al usuario escribir instrucciones completamente personalizadas.
        
        @returns {str} Instrucciones personalizadas
        """
        print("\n✍️ Escribir instrucciones personalizadas:")
        print("💡 Puedes escribir múltiples líneas. Presiona Enter dos veces para finalizar.")
        print("📝 Ejemplo: 'Eres un asistente especializado en...'")
        
        lineas = []
        lineas_vacias_consecutivas = 0
        
        while True:
            try:
                linea = input()
                if not linea.strip():
                    lineas_vacias_consecutivas += 1
                    if lineas_vacias_consecutivas >= 2:
                        break
                else:
                    lineas_vacias_consecutivas = 0
                lineas.append(linea)
            except KeyboardInterrupt:
                print("\n❌ Operación cancelada")
                return None
        
        instrucciones_personalizadas = '\n'.join(lineas).strip()
        
        if not instrucciones_personalizadas:
            print("⚠️ No se ingresaron instrucciones. Operación cancelada.")
            return None
        
        print(f"\n📋 Instrucciones configuradas ({len(instrucciones_personalizadas)} caracteres)")
        return instrucciones_personalizadas
    
    def _modificar_instrucciones_por_defecto(self, instrucciones_base):
        """
        Permite al usuario modificar las instrucciones base proporcionadas.
        
        @param {str} instrucciones_base - Instrucciones base para modificar
        @returns {str} Instrucciones modificadas
        """
        print("\n🔧 Modificar instrucciones base:")
        print("💡 Las instrucciones actuales aparecerán línea por línea.")
        print("💡 Presiona Enter para mantener una línea, o escribe el reemplazo.")
        print("💡 Escribe 'SKIP' para omitir modificaciones y usar el original.")
        
        lineas_originales = instrucciones_base.split('\n')
        lineas_modificadas = []
        
        for i, linea in enumerate(lineas_originales, 1):
            print(f"\n--- Línea {i} ---")
            print(f"Original: {linea}")
            
            try:
                modificacion = input("Modificar (Enter para mantener, 'SKIP' para usar original): ")
                
                if modificacion.upper() == 'SKIP':
                    return instrucciones_base
                elif modificacion.strip():
                    lineas_modificadas.append(modificacion)
                else:
                    lineas_modificadas.append(linea)
                    
            except KeyboardInterrupt:
                print("\n❌ Modificación cancelada, usando original")
                return instrucciones_base
        
        # Permitir agregar líneas adicionales
        print("\n➕ ¿Deseas agregar líneas adicionales? (Enter para terminar)")
        while True:
            try:
                linea_adicional = input("Línea adicional: ")
                if not linea_adicional.strip():
                    break
                lineas_modificadas.append(linea_adicional)
            except KeyboardInterrupt:
                break
        
        instrucciones_modificadas = '\n'.join(lineas_modificadas)
        print(f"\n📋 Instrucciones modificadas ({len(instrucciones_modificadas)} caracteres)")
        return instrucciones_modificadas

    def _obtener_instrucciones_por_defecto(self):
        """
        Este método se mantiene para compatibilidad con código existente pero ya no retorna valores por defecto.
        
        @returns {str} None - No hay instrucciones por defecto
        """
        print("⚠️ No hay instrucciones por defecto disponibles.")
        print("💡 Debes configurar las instrucciones manualmente.")
        return None

    def actualizar_agente(self, agent_id=None):
        """
        Actualiza un agente existente.
        
        @param {str} agent_id - ID del agente a actualizar (opcional)
        @returns {bool} True si se actualizó exitosamente
        """
        with trazador.start_as_current_span("actualizar_agente") as span:
            try:
                # Si no se proporciona ID, permitir seleccionar
                if agent_id is None:
                    agent_id = self._seleccionar_agente_para_actualizar()
                    if not agent_id:
                        return False
                
                # Obtener información actual del agente
                agente_info = self._obtener_info_agente(agent_id)
                if not agente_info:
                    print(f"❌ No se encontró información del agente {agent_id}")
                    return False
                
                print(f"\n🔧 Actualizando agente: {agente_info['nombre']}")
                print(f"🆔 ID: {agent_id}")
                print(f"📊 Tipo: {agente_info['tipo']}")
                
                # Opciones de actualización
                print("\n📋 ¿Qué deseas actualizar?")
                print("1. Nombre del agente")
                print("2. Instrucciones/Prompt")
                print("3. Ambos (nombre e instrucciones)")
                print("0. Cancelar")
                
                while True:
                    opcion = input("\nSelecciona una opción (0-3): ").strip()
                    
                    if opcion == "0":
                        print("❌ Actualización cancelada")
                        return False
                    elif opcion in ["1", "2", "3"]:
                        break
                    else:
                        print("❌ Opción no válida")
                
                # Configurar nuevos valores
                nuevo_nombre = agente_info['nombre']
                nuevas_instrucciones = agente_info['instrucciones']
                
                if opcion in ["1", "3"]:
                    nuevo_nombre_input = input(f"\n📝 Nuevo nombre (Enter para mantener '{agente_info['nombre']}'): ").strip()
                    if nuevo_nombre_input:
                        nuevo_nombre = nuevo_nombre_input
                
                if opcion in ["2", "3"]:
                    print(f"\n📋 Instrucciones actuales:")
                    print(f"'{agente_info['instrucciones']}'")
                    print("\n¿Deseas modificar las instrucciones?")
                    modificar = input("(S/n): ").strip().lower()
                    if modificar != 'n' and modificar != 'no':
                        nuevas_instrucciones = self._obtener_instrucciones_personalizadas()
                
                # Confirmar actualización
                print(f"\n📋 Resumen de cambios:")
                print(f"Nombre: {agente_info['nombre']} → {nuevo_nombre}")
                print(f"Instrucciones: {'Modificadas' if nuevas_instrucciones != agente_info['instrucciones'] else 'Sin cambios'}")
                
                confirmar = input("\n¿Confirmar actualización? (S/n): ").strip().lower()
                if confirmar in ['n', 'no']:
                    print("❌ Actualización cancelada")
                    return False
                
                # Realizar actualización en el servicio
                with self._get_client() as cliente:
                    agente_actualizado = cliente.update_agent(
                        agent_id=agent_id,
                        name=nuevo_nombre,
                        instructions=nuevas_instrucciones
                    )
                
                # Actualizar información local
                self._actualizar_info_agente_local(agent_id, nuevo_nombre, nuevas_instrucciones)
                
                span.set_attribute("agent.id", agent_id)
                span.set_attribute("agent.updated", True)
                span.set_attribute("agent.name_changed", nuevo_nombre != agente_info['nombre'])
                span.set_attribute("agent.instructions_changed", nuevas_instrucciones != agente_info['instrucciones'])
                
                print(f"✅ Agente '{nuevo_nombre}' actualizado exitosamente")
                return True
                
            except Exception as e:
                span.record_exception(e)
                print(f"❌ Error al actualizar agente: {e}")
                return False
    
    def _seleccionar_agente_para_actualizar(self):
        """
        Permite seleccionar un agente para actualizar.
        
        @returns {str|None} ID del agente seleccionado o None si se cancela
        """
        agentes = self.obtener_agentes_existentes()
        
        if not agentes:
            print("📭 No hay agentes disponibles para actualizar")
            return None
        
        print("\n🔧 Selecciona el agente a actualizar:")
        print("=" * 50)
        
        for i, agente in enumerate(agentes, 1):
            print(f"{i}. {agente['nombre']} ({agente['tipo']})")
            print(f"   ID: {agente['id']}")
            print(f"   Creado: {agente.get('fecha_creacion', 'N/A')}")
            print()
        
        print("0. Cancelar")
        
        while True:
            try:
                opcion = input("\nIngresa tu opción: ").strip()
                
                if opcion == "0":
                    return None
                
                indice = int(opcion) - 1
                if 0 <= indice < len(agentes):
                    return agentes[indice]['id']
                else:
                    print("❌ Opción no válida")
                    
            except ValueError:
                print("❌ Por favor ingresa un número válido")
            except KeyboardInterrupt:
                return None
    
    def _obtener_info_agente(self, agent_id):
        """
        Obtiene la información de un agente específico.
        
        @param {str} agent_id - ID del agente
        @returns {dict|None} Información del agente o None si no se encuentra
        """
        agentes = self.obtener_agentes_existentes()
        for agente in agentes:
            if agente['id'] == agent_id:
                return agente
        return None
    
    def _actualizar_info_agente_local(self, agent_id, nuevo_nombre, nuevas_instrucciones):
        """
        Actualiza la información local del agente.
        
        @param {str} agent_id - ID del agente
        @param {str} nuevo_nombre - Nuevo nombre del agente
        @param {str} nuevas_instrucciones - Nuevas instrucciones del agente
        """
        try:
            agentes = self.obtener_agentes_existentes()
            
            for agente in agentes:
                if agente['id'] == agent_id:
                    agente['nombre'] = nuevo_nombre
                    agente['instrucciones'] = nuevas_instrucciones
                    agente['fecha_actualizacion'] = self._obtener_fecha_actual()
                    break
            
            # Guardar cambios
            agentes_json = json.dumps(agentes, ensure_ascii=False, indent=2)
            set_key(self.archivo_env, "AGENTS_DATA", agentes_json)
            load_dotenv(self.archivo_env, override=True)
            
            print("💾 Información local actualizada")
            
        except Exception as e:
            print(f"⚠️ Error al actualizar información local: {e}")

    def guardar_agente(self, agent_id, nombre, tipo_agente, instrucciones):
        """
        Guarda la información del agente en el archivo .env.
        
        @param {str} agent_id - ID del agente
        @param {str} nombre - Nombre del agente
        @param {str} tipo_agente - Tipo de agente
        @param {str} instrucciones - Instrucciones del agente
        """
        try:
            # Obtener agentes existentes
            agentes_existentes = self.obtener_agentes_existentes()
            
            # Agregar nuevo agente
            nuevo_agente = {
                "id": agent_id,
                "nombre": nombre,
                "tipo": tipo_agente,
                "instrucciones": instrucciones,
                "fecha_creacion": self._obtener_fecha_actual()
            }
            
            agentes_existentes.append(nuevo_agente)
            
            # Guardar en archivo .env como JSON
            agentes_json = json.dumps(agentes_existentes, ensure_ascii=False, indent=2)
            set_key(self.archivo_env, "AGENTS_DATA", agentes_json)
            
            # También mantener AGENT_ID para compatibilidad (usar el último creado)
            set_key(self.archivo_env, "AGENT_ID", agent_id)
            
            # Recargar variables de entorno
            load_dotenv(self.archivo_env, override=True)
            
            print(f"💾 Agente guardado. Total de agentes: {len(agentes_existentes)}")
                
        except Exception as e:
            print(f"⚠️ Error al guardar información del agente: {e}")
    
    def obtener_agentes_existentes(self):
        """
        Obtiene la lista de agentes existentes desde variables de entorno.
        
        @returns {list} Lista de agentes con su información
        """
        try:
            agentes_json = os.environ.get("AGENTS_DATA", "[]")
            agentes = json.loads(agentes_json)
            
            # Validar que los agentes existen en el servicio
            agentes_validos = []
            with self._get_client() as cliente:
                for agente_info in agentes:
                    try:
                        agente = cliente.get_agent(agente_info["id"])
                        agentes_validos.append(agente_info)
                    except Exception:
                        print(f"⚠️ Agente {agente_info['nombre']} ({agente_info['id']}) no encontrado en el servicio")
            
            # Actualizar la lista si hay cambios
            if len(agentes_validos) != len(agentes):
                self._actualizar_lista_agentes(agentes_validos)
            
            return agentes_validos
            
        except json.JSONDecodeError:
            print("⚠️ Error al leer datos de agentes, iniciando lista vacía")
            return []
        except Exception as e:
            print(f"⚠️ Error al obtener agentes existentes: {e}")
            return []
    
    def _actualizar_lista_agentes(self, agentes_validos):
        """
        Actualiza la lista de agentes en el archivo .env.
        
        @param {list} agentes_validos - Lista de agentes válidos
        """
        try:
            agentes_json = json.dumps(agentes_validos, ensure_ascii=False, indent=2)
            set_key(self.archivo_env, "AGENTS_DATA", agentes_json)
            load_dotenv(self.archivo_env, override=True)
        except Exception as e:
            print(f"⚠️ Error al actualizar lista de agentes: {e}")
    
    def _obtener_fecha_actual(self):
        """
        Obtiene la fecha actual en formato ISO.
        
        @returns {str} Fecha actual
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def listar_agentes(self):
        """
        Lista todos los agentes existentes.
        """
        agentes = self.obtener_agentes_existentes()
        
        if not agentes:
            print("📭 No hay agentes creados")
            return
        
        print(f"🤖 Agentes disponibles ({len(agentes)}):")
        print("=" * 50)
        
        for i, agente in enumerate(agentes, 1):
            print(f"{i}. {agente['nombre']}")
            print(f"   ID: {agente['id']}")
            print(f"   Tipo: {agente['tipo']}")
            print(f"   Creado: {agente.get('fecha_creacion', 'N/A')}")
            print()
    
    def limpiar_agente(self, agent_id):
        """
        Elimina un agente del servicio y de la lista local.
        
        @param {str} agent_id - ID del agente a eliminar
        """
        try:
            # Eliminar del servicio
            with self._get_client() as cliente:
                cliente.delete_agent(agent_id)
                print(f"🗑️ Agente {agent_id} eliminado del servicio")
            
            # Eliminar de la lista local
            agentes_existentes = self.obtener_agentes_existentes()
            agentes_filtrados = [a for a in agentes_existentes if a["id"] != agent_id]
            self._actualizar_lista_agentes(agentes_filtrados)
            
            print(f"💾 Agente removido de la lista local")
            
        except Exception as e:
            print(f"⚠️ Error al eliminar agente {agent_id}: {e}")

    def recargar_variables_entorno(self):
        """
        Recarga todas las variables de entorno desde el archivo .env.
        """
        try:
            load_dotenv(self.archivo_env, override=True)
            print("🔄 Variables de entorno recargadas desde .env")
        except Exception as e:
            print(f"⚠️ Error al recargar variables de entorno: {e}")

    def obtener_agente_existente(self):
        """
        Obtiene el ID del agente existente desde variables de entorno (para compatibilidad).
        
        @returns {str|None} ID del agente existente o None si no existe
        """
        return os.environ.get("AGENT_ID")
    
    def _obtener_tipo_agente(self):
        """
        Solicita al usuario que seleccione el tipo de agente a crear.
        
        @returns {str} Tipo de agente seleccionado
        """
        print("\n🤖 Selecciona el tipo de agente a crear:")
        print("1. Básico - Agente conversacional simple")
        print("2. MCP - Agente con Model Context Protocol (MCP)")
        print("3. Azure Function - Agente con funciones de Azure")
        
        while True:
            try:
                opcion = input("\nIngresa tu opción (1-3): ").strip()
                
                if opcion == "1":
                    return "basico"
                elif opcion == "2":
                    return "mcp"
                elif opcion == "3":
                    return "azure_function"
                else:
                    print("❌ Opción no válida. Por favor ingresa 1, 2 o 3.")
                    
            except KeyboardInterrupt:
                print("\n❌ Operación cancelada por el usuario")
                sys.exit(1)
    
    def _crear_agente_basico(self, nombre, instrucciones):
        """
        Crea un agente conversacional básico.
        
        @param {str} nombre - Nombre del agente
        @param {str} instrucciones - Instrucciones del sistema
        @returns Objeto agente creado
        """
        with self._get_client() as cliente:
            return cliente.create_agent(
                model=os.environ["MODEL_DEPLOYMENT_NAME"],
                name=nombre,
                instructions=instrucciones
            )
    
    def _validar_url(self, url):
        """
        Valida que una URL tenga formato básico correcto.
        
        @param {str} url - URL a validar
        @returns {bool} True si la URL es válida
        """
        import re
        patron_url = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(patron_url, url))
    
    def _obtener_configuracion_mcp(self):
        """
        Obtiene la configuración del servidor MCP del usuario.
        
        @returns {dict} Configuración del servidor MCP
        """
        print("\n🔧 Configuración del servidor MCP:")
        print("=" * 50)
        print("💡 El servidor MCP permite al agente acceder a servicios externos")
        print("💡 Necesitas configurar la URL y etiqueta del servidor")
        
        # Verificar si hay configuración en variables de entorno
        server_url_env = os.environ.get("MCP_SERVER_URL", "")
        server_label_env = os.environ.get("MCP_SERVER_LABEL", "Chuck Norris MCP")
        
        if server_url_env:
            print(f"\n📋 Configuración encontrada en variables de entorno:")
            print(f"   URL: {server_url_env}")
            print(f"   Etiqueta: {server_label_env}")
            
            usar_env = input("\n¿Usar configuración de variables de entorno? (S/n): ").strip().lower()
            if usar_env not in ['n', 'no']:
                return {
                    "server_url": server_url_env,
                    "server_label": server_label_env
                }
        
        # Solicitar configuración manual
        print("\n📝 Configuración manual del servidor MCP:")
        
        # URL del servidor
        while True:
            server_url = input("🌐 URL del servidor MCP (ej: http://localhost:8080): ").strip()
            if server_url:
                # Validar formato básico de URL
                if self._validar_url(server_url):
                    break
                else:
                    print("❌ URL no válida. Use formato: http://localhost:puerto o https://dominio.com")
            else:
                print("❌ La URL del servidor es obligatoria")
        
        # Etiqueta del servidor
        server_label = input(f"🏷️  Etiqueta del servidor (Enter para '{server_label_env}'): ").strip()
        if not server_label:
            server_label = server_label_env
        
        # Configuración de aprobación
        print("\n🔐 Configuración de aprobación:")
        print("1. never - No requiere aprobación (recomendado para desarrollo)")
        print("2. once - Requiere aprobación una vez")
        print("3. always - Siempre requiere aprobación")
        
        while True:
            opcion_aprobacion = input("\nSelecciona opción de aprobación (1-3): ").strip()
            if opcion_aprobacion == "1":
                require_approval = "never"
                break
            elif opcion_aprobacion == "2":
                require_approval = "once"
                break
            elif opcion_aprobacion == "3":
                require_approval = "always"
                break
            else:
                print("❌ Opción no válida")
        
        configuracion = {
            "server_url": server_url,
            "server_label": server_label,
            "require_approval": require_approval
        }
        
        # Preguntar si guardar en variables de entorno
        guardar_env = input("\n💾 ¿Guardar configuración en variables de entorno? (S/n): ").strip().lower()
        if guardar_env not in ['n', 'no']:
            self._guardar_configuracion_mcp_env(configuracion)
        
        return configuracion
    
    def _guardar_configuracion_mcp_env(self, configuracion):
        """
        Guarda la configuración MCP en variables de entorno.
        
        @param {dict} configuracion - Configuración a guardar
        """
        try:
            set_key(self.archivo_env, "MCP_SERVER_URL", configuracion["server_url"])
            set_key(self.archivo_env, "MCP_SERVER_LABEL", configuracion["server_label"])
            set_key(self.archivo_env, "MCP_REQUIRE_APPROVAL", configuracion["require_approval"])
            
            # Recargar variables de entorno
            load_dotenv(self.archivo_env, override=True)
            
            print("✅ Configuración MCP guardada en .env")
            print("💡 Podrás reutilizar esta configuración en futuros agentes")
            
        except Exception as e:
            print(f"⚠️ Error al guardar configuración MCP: {e}")

    def _obtener_configuracion_azure_function(self):
        """
        Obtiene la configuración de Azure Functions del usuario.
        
        @returns {dict} Configuración de Azure Functions
        """
        print("\n🔧 Configuración de Azure Functions:")
        print("=" * 50)
        print("💡 Azure Functions permite al agente ejecutar código serverless")
        print("💡 Necesitas configurar las colas de entrada y salida")
        
        # Verificar configuración en variables de entorno
        queue_service_uri_env = os.environ.get("AZURE_QUEUE_SERVICE_URI", "")
        input_queue_env = os.environ.get("AZURE_INPUT_QUEUE", "input")
        output_queue_env = os.environ.get("AZURE_OUTPUT_QUEUE", "output")
        function_name_env = os.environ.get("AZURE_FUNCTION_NAME", "pocazureaifoundry")
        
        if queue_service_uri_env:
            print(f"\n📋 Configuración encontrada en variables de entorno:")
            print(f"   URI del servicio: {queue_service_uri_env}")
            print(f"   Cola de entrada: {input_queue_env}")
            print(f"   Cola de salida: {output_queue_env}")
            print(f"   Nombre de función: {function_name_env}")
            
            usar_env = input("\n¿Usar configuración de variables de entorno? (S/n): ").strip().lower()
            if usar_env not in ['n', 'no']:
                return {
                    "queue_service_uri": queue_service_uri_env,
                    "input_queue": input_queue_env,
                    "output_queue": output_queue_env,
                    "function_name": function_name_env
                }
        
        # Solicitar configuración manual
        print("\n📝 Configuración manual de Azure Functions:")
        
        # URI del servicio de colas
        while True:
            queue_service_uri = input("🌐 URI del servicio de colas (ej: https://storage.queue.core.windows.net): ").strip()
            if queue_service_uri:
                if self._validar_url(queue_service_uri):
                    break
                else:
                    print("❌ URI no válida. Use formato: https://nombre.queue.core.windows.net")
            else:
                print("❌ El URI del servicio de colas es obligatorio")
        
        # Nombres de colas
        input_queue = input(f"📥 Nombre de cola de entrada (Enter para '{input_queue_env}'): ").strip()
        if not input_queue:
            input_queue = input_queue_env
            
        output_queue = input(f"📤 Nombre de cola de salida (Enter para '{output_queue_env}'): ").strip()
        if not output_queue:
            output_queue = output_queue_env
        
        # Nombre de la función
        function_name = input(f"⚙️  Nombre de la función (Enter para '{function_name_env}'): ").strip()
        if not function_name:
            function_name = function_name_env
        
        configuracion = {
            "queue_service_uri": queue_service_uri,
            "input_queue": input_queue,
            "output_queue": output_queue,
            "function_name": function_name
        }
        
        # Preguntar si guardar en variables de entorno
        guardar_env = input("\n💾 ¿Guardar configuración en variables de entorno? (S/n): ").strip().lower()
        if guardar_env not in ['n', 'no']:
            self._guardar_configuracion_azure_function_env(configuracion)
        
        return configuracion
    
    def _guardar_configuracion_azure_function_env(self, configuracion):
        """
        Guarda la configuración de Azure Functions en variables de entorno.
        
        @param {dict} configuracion - Configuración a guardar
        """
        try:
            set_key(self.archivo_env, "AZURE_QUEUE_SERVICE_URI", configuracion["queue_service_uri"])
            set_key(self.archivo_env, "AZURE_INPUT_QUEUE", configuracion["input_queue"])
            set_key(self.archivo_env, "AZURE_OUTPUT_QUEUE", configuracion["output_queue"])
            set_key(self.archivo_env, "AZURE_FUNCTION_NAME", configuracion["function_name"])
            
            # Recargar variables de entorno
            load_dotenv(self.archivo_env, override=True)
            
            print("✅ Configuración Azure Functions guardada en .env")
            print("💡 Podrás reutilizar esta configuración en futuros agentes")
            
        except Exception as e:
            print(f"⚠️ Error al guardar configuración Azure Functions: {e}")
    
    def _crear_agente_mcp(self, nombre, instrucciones):
        """
        Crea un agente con Model Context Protocol (MCP).
        
        @param {str} nombre - Nombre del agente
        @param {str} instrucciones - Instrucciones del sistema
        @returns Objeto agente creado
        """
        # Obtener configuración MCP del usuario
        config_mcp = self._obtener_configuracion_mcp()
        
        with self._get_client() as cliente:
            return cliente.create_agent(
                model=os.environ["MODEL_DEPLOYMENT_NAME"],
                name=nombre,
                instructions=instrucciones,
                tools=[
                    {
                        "type": "mcp",
                        "server_label": config_mcp["server_label"],
                        "server_url": config_mcp["server_url"],
                        "require_approval": config_mcp["require_approval"]
                    }
                ],
                tool_resources=None
            )
    
    def _crear_agente_azure_function(self, nombre, instrucciones):
        """
        Crea un agente con funciones de Azure.
        
        @param {str} nombre - Nombre del agente
        @param {str} instrucciones - Instrucciones del sistema
        @returns Objeto agente creado
        """
        # Obtener configuración de Azure Functions del usuario
        config_func = self._obtener_configuracion_azure_function()
        
        with self._get_client() as cliente:
            return cliente.create_agent(
                model=os.environ["MODEL_DEPLOYMENT_NAME"],
                name=nombre,
                instructions=instrucciones,
                tools=[
                    {
                        "type": "azure_function",
                        "azure_function": {
                            "input_binding": {
                                "type": "storage_queue",
                                "storage_queue": {
                                    "queue_service_uri": config_func["queue_service_uri"],
                                    "queue_name": config_func["input_queue"]
                                }
                            },
                            "output_binding": {
                                "type": "storage_queue",
                                "storage_queue": {
                                    "queue_service_uri": config_func["queue_service_uri"],
                                    "queue_name": config_func["output_queue"]
                                }
                            },
                            "function": {
                                "name": config_func["function_name"],
                                "description": "Estado del pedido activo.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "customer_id": {
                                            "type": "string"
                                        }
                                    },
                                    "required": [
                                        "customer_id"
                                    ]
                                }
                            }
                        }
                    }
                ],
                tool_resources=None
            )

def main():
    """
    Función principal para crear o gestionar agentes.
    """
    print("🤖 Gestor de Agentes Azure AI")
    print("=" * 40)
    
    gestor = GestorAgente()
    
    # Recargar variables de entorno al inicio
    gestor.recargar_variables_entorno()
    
    # Mostrar menú de opciones
    print("\n📋 Opciones disponibles:")
    print("1. Crear nuevo agente")
    print("2. Actualizar agente existente")
    print("3. Listar agentes existentes")
    print("4. Eliminar agente")
    print("0. Salir")
    
    while True:
        try:
            opcion = input("\nSelecciona una opción: ").strip()
            
            if opcion == "0":
                print("👋 ¡Hasta luego!")
                break
            elif opcion == "1":
                # Crear nuevo agente
                gestor.crear_agente()
                break
            elif opcion == "2":
                # Actualizar agente existente
                if gestor.actualizar_agente():
                    print("💡 Puedes continuar gestionando agentes o salir.")
                else:
                    print("💡 No se realizaron cambios.")
            elif opcion == "3":
                # Listar agentes
                gestor.listar_agentes()
                input("\nPresiona Enter para continuar...")
            elif opcion == "4":
                # Eliminar agente
                agentes = gestor.obtener_agentes_existentes()
                if not agentes:
                    print("📭 No hay agentes para eliminar")
                    continue
                
                print("\n🗑️ Selecciona el agente a eliminar:")
                for i, agente in enumerate(agentes, 1):
                    print(f"{i}. {agente['nombre']} ({agente['id']})")
                
                try:
                    indice = int(input("\nIngresa el número: ").strip()) - 1
                    if 0 <= indice < len(agentes):
                        agente_a_eliminar = agentes[indice]
                        confirmacion = input(f"¿Confirmas eliminar '{agente_a_eliminar['nombre']}'? (s/N): ").strip().lower()
                        if confirmacion in ['s', 'si', 'sí', 'y', 'yes']:
                            gestor.limpiar_agente(agente_a_eliminar['id'])
                        else:
                            print("❌ Cancelado")
                    else:
                        print("❌ Número no válido")
                except ValueError:
                    print("❌ Por favor ingresa un número válido")
            else:
                print("❌ Opción no válida")
                
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
    
    print("\n🎉 Gestión de agentes completada!")
    print("💡 Ahora puedes ejecutar: python conversar_agente.py")
