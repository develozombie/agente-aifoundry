#!/usr/bin/env python3
"""
INICIO.PY - Orquestador Principal del Sistema de Agentes
===========================================================

DESCRIPCIÓN:
    Archivo principal que organiza y ejecuta todas las funciones del sistema
    con un menú interactivo mejorado.

FUNCIONALIDADES:
    - Menú principal interactivo
    - Inicio opcional del servidor MCP
    - Gestión interactiva de agentes
    - Selección y conversación con agentes
    - Manejo robusto de errores y excepciones
"""

import os
import sys
import time
import subprocess
import signal
import json
from pathlib import Path
from dotenv import load_dotenv

# Configurar encoding UTF-8
if sys.platform.startswith('win'):
    import locale
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
else:
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Cargar variables de entorno
load_dotenv(encoding='utf-8')

class OrquestadorInicio:
    """
    Clase principal que orquesta la ejecución de todas las funciones del sistema.
    """
    
    def __init__(self):
        """
        Inicializa el orquestador con configuración básica.
        """
        self.mcp_proceso = None
        self.mcp_activo = False
        self.directorio_trabajo = Path(__file__).parent
        self.archivo_mcp = self.directorio_trabajo / "chuck_norris_server.py"
        
        # Configurar manejo de señales para limpieza
        signal.signal(signal.SIGINT, self._manejar_interrupcion)
        signal.signal(signal.SIGTERM, self._manejar_interrupcion)
    
    def _manejar_interrupcion(self, signum, frame):
        """
        Maneja interrupciones del sistema para limpieza ordenada.
        """
        print("\n🛑 Interrupción detectada, realizando limpieza...")
        self._detener_mcp()
        print("👋 ¡Hasta luego!")
        sys.exit(0)
    
    def mostrar_bienvenida(self):
        """
        Muestra el banner de bienvenida del sistema.
        """
        print("\n" + "=" * 80)
        print("🚀 SISTEMA DE AGENTES AZURE AI FOUNDRY")
        print("=" * 80)
        print("🤖 Bienvenido al sistema integrado de agentes conversacionales")
        print("💫 Este sistema te permitirá gestionar y conversar con agentes de IA")
        print("=" * 80)
    
    def validar_entorno(self):
        """
        Valida que el entorno esté correctamente configurado.
        """
        # Variables de entorno requeridas
        variables_requeridas = [
            "PROJECT_ENDPOINT",
            "MODEL_DEPLOYMENT_NAME"
        ]
        
        variables_faltantes = []
        for variable in variables_requeridas:
            if not os.environ.get(variable):
                variables_faltantes.append(variable)
        
        if variables_faltantes:
            print("❌ Variables de entorno faltantes:")
            for variable in variables_faltantes:
                print(f"   - {variable}")
            print("\n💡 Configura estas variables en tu archivo .env")
            return False
        
        # Validar archivos necesarios
        archivos_requeridos = [
            "chuck_norris_server.py",
            "crear_agente.py", 
            "conversar_agente.py"
        ]
        
        archivos_faltantes = []
        for archivo in archivos_requeridos:
            if not (self.directorio_trabajo / archivo).exists():
                archivos_faltantes.append(archivo)
        
        if archivos_faltantes:
            print("❌ Archivos faltantes:")
            for archivo in archivos_faltantes:
                print(f"   - {archivo}")
            return False
        
        return True
    
    def obtener_opcion_usuario(self, mensaje, opciones_validas, mostrar_opciones=True):
        """
        Obtiene una opción válida del usuario.
        """
        while True:
            if mostrar_opciones:
                print(f"\n{mensaje}")
            try:
                opcion = input("👉 Selecciona una opción: ").strip()
                
                if opcion in opciones_validas:
                    return opcion
                else:
                    print(f"❌ Opción no válida. Por favor selecciona: {', '.join(opciones_validas)}")
                    
            except KeyboardInterrupt:
                print("\n❌ Operación cancelada")
                return None
            except EOFError:
                print("\n❌ Entrada finalizada")
                return None
    
    def mostrar_menu_principal(self):
        """
        Muestra el menú principal del sistema.
        """
        estado_mcp = "🟢 ACTIVO" if self.mcp_activo else "🔴 INACTIVO"
        
        print(f"\n📋 MENÚ PRINCIPAL")
        print(f"   Estado MCP: {estado_mcp}")
        print("=" * 50)
        print("1. 🔧 Gestionar Agentes")
        print("2. 💬 Conversar con Agentes")
        print("3. 🚀 Iniciar/Detener Servidor MCP")
        print("4. 📊 Ver Estado del Sistema")
        print("5. ❌ Salir")
        
        return self.obtener_opcion_usuario("¿Qué deseas hacer?", ["1", "2", "3", "4", "5"], False)
    
    def iniciar_mcp(self):
        """
        Inicia el servidor MCP (Model Context Protocol).
        """
        if self.mcp_activo:
            print("⚠️ El servidor MCP ya está activo")
            return True
            
        print("\n🚀 Iniciando servidor MCP...")
        
        if not self.archivo_mcp.exists():
            print(f"❌ No se encontró el archivo {self.archivo_mcp}")
            return False
        
        try:
            print(f"📁 Ejecutando: {self.archivo_mcp}")
            
            # Iniciar el servidor en modo background
            self.mcp_proceso = subprocess.Popen(
                [sys.executable, str(self.archivo_mcp)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.directorio_trabajo)
            )
            
            # Dar tiempo para que el servidor se inicie
            time.sleep(2)
            
            # Verificar que el proceso siga corriendo
            if self.mcp_proceso.poll() is None:
                self.mcp_activo = True
                print("✅ Servidor MCP iniciado correctamente")
                print(f"🆔 PID del proceso: {self.mcp_proceso.pid}")
                return True
            else:
                # El proceso terminó, obtener error
                stdout, stderr = self.mcp_proceso.communicate()
                print("❌ Error al iniciar servidor MCP:")
                if stderr:
                    print(f"Error: {stderr}")
                if stdout:
                    print(f"Salida: {stdout}")
                return False
                
        except Exception as e:
            print(f"❌ Error al iniciar servidor MCP: {e}")
            return False
    
    def detener_mcp(self):
        """
        Detiene el servidor MCP.
        """
        if not self.mcp_activo:
            print("⚠️ El servidor MCP no está activo")
            return True
            
        return self._detener_mcp()
    
    def _detener_mcp(self):
        """
        Detiene el servidor MCP de manera ordenada.
        """
        if self.mcp_proceso and self.mcp_proceso.poll() is None:
            print("🛑 Deteniendo servidor MCP...")
            try:
                self.mcp_proceso.terminate()
                self.mcp_proceso.wait(timeout=5)
                self.mcp_activo = False
                print("✅ Servidor MCP detenido correctamente")
                return True
            except subprocess.TimeoutExpired:
                print("⚠️ Forzando cierre del servidor MCP...")
                self.mcp_proceso.kill()
                self.mcp_proceso.wait()
                self.mcp_activo = False
                print("✅ Servidor MCP cerrado forzosamente")
                return True
            except Exception as e:
                print(f"⚠️ Error al detener servidor MCP: {e}")
                return False
        else:
            self.mcp_activo = False
            return True
    
    def gestionar_mcp(self):
        """
        Gestiona el servidor MCP (iniciar/detener).
        """
        if self.mcp_activo:
            print("\n🟢 El servidor MCP está actualmente ACTIVO")
            opcion = self.obtener_opcion_usuario(
                "¿Qué deseas hacer?\n1. Detener servidor\n2. Volver al menú principal",
                ["1", "2"]
            )
            if opcion == "1":
                self.detener_mcp()
            # Opción 2 simplemente regresa
        else:
            print("\n🔴 El servidor MCP está actualmente INACTIVO")
            opcion = self.obtener_opcion_usuario(
                "¿Qué deseas hacer?\n1. Iniciar servidor\n2. Volver al menú principal",
                ["1", "2"]
            )
            if opcion == "1":
                self.iniciar_mcp()
            # Opción 2 simplemente regresa
    
    def gestionar_agentes(self):
        """
        Ejecuta la gestión de agentes.
        """
        print("\n🤖 GESTIÓN DE AGENTES")
        print("=" * 30)
        
        try:
            # Importar y ejecutar el gestor de agentes
            sys.path.insert(0, str(self.directorio_trabajo))
            from crear_agente import GestorAgente
            
            gestor = GestorAgente()
            
            # Mostrar agentes existentes
            agentes_existentes = gestor.obtener_agentes_existentes()
            
            if agentes_existentes:
                print(f"📋 Agentes existentes ({len(agentes_existentes)}):")
                for i, agente in enumerate(agentes_existentes, 1):
                    print(f"   {i}. {agente['nombre']} ({agente['tipo']})")
                    print(f"      ID: {agente['id']}")
                    fecha = agente.get('fecha_creacion', 'N/A')
                    if len(fecha) > 19:  # Truncar fecha si es muy larga
                        fecha = fecha[:19]
                    print(f"      Creado: {fecha}")
                
                opcion = self.obtener_opcion_usuario(
                    "¿Qué deseas hacer?\n1. Usar agentes existentes\n2. Crear nuevo agente\n3. Actualizar agente existente\n4. Eliminar agente\n5. Volver al menú principal",
                    ["1", "2", "3", "4", "5"]
                )
                
                if opcion == "1":
                    print("✅ Continuando con agentes existentes")
                    return True
                elif opcion == "2":
                    print("\n🔧 Creando nuevo agente...")
                    agent_id = gestor.crear_agente()
                    if agent_id:
                        print("✅ Nuevo agente creado exitosamente")
                        return True
                    else:
                        print("❌ No se pudo crear el agente")
                        return False
                elif opcion == "3":
                    print("\n🔧 Actualizando agente...")
                    if gestor.actualizar_agente():
                        print("✅ Agente actualizado exitosamente")
                        return True
                    else:
                        print("❌ No se pudo actualizar el agente")
                        return False
                elif opcion == "4":
                    # Eliminar agente
                    print("\nSelecciona el agente a eliminar:")
                    for i, agente in enumerate(agentes_existentes, 1):
                        print(f"{i}. {agente['nombre']}")
                    
                    opciones_validas = [str(i) for i in range(1, len(agentes_existentes) + 1)]
                    opciones_validas.append("0")  # Para cancelar
                    
                    indice_str = self.obtener_opcion_usuario(
                        "Ingresa el número del agente (0 para cancelar):",
                        opciones_validas,
                        False
                    )
                    
                    if indice_str == "0" or indice_str is None:
                        print("❌ Cancelado")
                        return True
                    
                    indice = int(indice_str) - 1
                    agente_a_eliminar = agentes_existentes[indice]
                    
                    confirmacion = self.obtener_opcion_usuario(
                        f"¿Confirmas eliminar '{agente_a_eliminar['nombre']}'?\n1. Sí, eliminar\n2. No, cancelar",
                        ["1", "2"]
                    )
                    
                    if confirmacion == "1":
                        gestor.limpiar_agente(agente_a_eliminar['id'])
                        print("✅ Agente eliminado")
                        return True
                    else:
                        print("❌ Cancelado")
                        return True
                elif opcion == "5":
                    return True
                else:
                    return True
            else:
                # No hay agentes existentes, crear uno nuevo
                print("📭 No se encontraron agentes existentes")
                opcion = self.obtener_opcion_usuario(
                    "¿Qué deseas hacer?\n1. Crear primer agente\n2. Volver al menú principal",
                    ["1", "2"]
                )
                
                if opcion == "1":
                    print("🔧 Creando primer agente...")
                    agent_id = gestor.crear_agente()
                    if agent_id:
                        print("✅ Primer agente creado exitosamente")
                        return True
                    else:
                        print("❌ No se pudo crear el agente")
                        return False
                else:
                    return True
                    
        except ImportError as e:
            print(f"❌ Error al importar gestor de agentes: {e}")
            return False
        except Exception as e:
            print(f"❌ Error en gestión de agentes: {e}")
            return False
    
    def conversar_con_agentes(self):
        """
        Inicia la conversación con agentes.
        """
        print("\n💬 CONVERSACIÓN CON AGENTES")
        print("=" * 35)
        
        try:
            # Verificar si hay agentes disponibles
            agentes_json = os.environ.get("AGENTS_DATA", "[]")
            agentes = json.loads(agentes_json)
            
            if not agentes:
                print("❌ No hay agentes disponibles para conversar")
                opcion = self.obtener_opcion_usuario(
                    "¿Qué deseas hacer?\n1. Ir a gestión de agentes\n2. Volver al menú principal",
                    ["1", "2"]
                )
                
                if opcion == "1":
                    return self.gestionar_agentes()
                else:
                    return True
            
            print(f"📋 Agentes disponibles ({len(agentes)}):")
            for i, agente in enumerate(agentes, 1):
                print(f"   {i}. {agente['nombre']}")
            
            opcion = self.obtener_opcion_usuario(
                "¿Qué deseas hacer?\n1. Iniciar conversación\n2. Volver al menú principal",
                ["1", "2"]
            )
            
            if opcion == "2":
                return True
            
            print("\n🚀 Iniciando sistema de conversación...")
            print("💡 Usa 'salir', 'quit' o 'exit' para terminar la conversación")
            
            # Ejecutar el sistema de conversación
            archivo_conversacion = self.directorio_trabajo / "conversar_agente.py"
            
            if not archivo_conversacion.exists():
                print(f"❌ No se encontró {archivo_conversacion}")
                return False
            
            print("\n🎯 Iniciando interfaz de conversación...")
            
            # Ejecutar el script de conversación
            resultado = subprocess.run(
                [sys.executable, str(archivo_conversacion)],
                cwd=str(self.directorio_trabajo)
            )
            
            if resultado.returncode == 0:
                print("\n✅ Sesión de conversación completada")
                return True
            else:
                print(f"\n⚠️ La conversación terminó con código: {resultado.returncode}")
                return True
                
        except json.JSONDecodeError:
            print("❌ Error al leer datos de agentes")
            return False
        except KeyboardInterrupt:
            print("\n❌ Conversación cancelada por el usuario")
            return True
        except Exception as e:
            print(f"❌ Error al iniciar conversación: {e}")
            return False
    
    def mostrar_estado_sistema(self):
        """
        Muestra el estado actual del sistema.
        """
        print("\n📊 ESTADO DEL SISTEMA")
        print("=" * 30)
        
        # Estado MCP
        estado_mcp = "🟢 ACTIVO" if self.mcp_activo else "🔴 INACTIVO"
        print(f"Servidor MCP: {estado_mcp}")
        
        if self.mcp_activo and self.mcp_proceso:
            print(f"PID del proceso: {self.mcp_proceso.pid}")
        
        # Estado de agentes
        try:
            agentes_json = os.environ.get("AGENTS_DATA", "[]")
            agentes = json.loads(agentes_json)
            print(f"Agentes disponibles: {len(agentes)}")
            
            if agentes:
                print("Lista de agentes:")
                for i, agente in enumerate(agentes, 1):
                    print(f"   {i}. {agente['nombre']} ({agente['tipo']})")
        except json.JSONDecodeError:
            print("Agentes disponibles: Error al leer datos")
        
        # Variables de entorno
        print(f"\nConfiguración:")
        print(f"   PROJECT_ENDPOINT: {'✅ Configurado' if os.environ.get('PROJECT_ENDPOINT') else '❌ No configurado'}")
        print(f"   MODEL_DEPLOYMENT_NAME: {'✅ Configurado' if os.environ.get('MODEL_DEPLOYMENT_NAME') else '❌ No configurado'}")
        
        input("\n📱 Presiona Enter para continuar...")
    
    def ejecutar(self):
        """
        Método principal que ejecuta el menú interactivo del sistema.
        """
        try:
            # Mostrar bienvenida
            self.mostrar_bienvenida()
            
            # Validar entorno
            if not self.validar_entorno():
                print("\n❌ Validación de entorno falló.")
                print("💡 Por favor configura las variables de entorno necesarias y vuelve a intentar.")
                return
            
            print("✅ Entorno validado correctamente")
            
            # Bucle principal del menú
            while True:
                opcion = self.mostrar_menu_principal()
                
                if opcion is None:  # Usuario canceló
                    break
                elif opcion == "1":
                    self.gestionar_agentes()
                elif opcion == "2":
                    self.conversar_con_agentes()
                elif opcion == "3":
                    self.gestionar_mcp()
                elif opcion == "4":
                    self.mostrar_estado_sistema()
                elif opcion == "5":
                    print("\n👋 ¡Gracias por usar el Sistema de Agentes Azure AI Foundry!")
                    break
                else:
                    print("❌ Opción no válida")
            
        except KeyboardInterrupt:
            print("\n🛑 Ejecución interrumpida por el usuario")
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")
        finally:
            # Limpieza final
            self._detener_mcp()

def main():
    """
    Función principal del programa.
    """
    try:
        orquestador = OrquestadorInicio()
        orquestador.ejecutar()
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()