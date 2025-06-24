# Ejemplo de agentes en Azure AI Foundry 🏦

## 🌟 Características

- **Moderación de Contenido**: Análisis de seguridad con Azure AI Content Safety
- **Instrumentación Completa**: Tracing y monitoreo con OpenTelemetry
- **Interfaz Conversacional**: Chat interactivo por línea de comandos
- **Persistencia de Agentes**: Reutilización de agentes entre sesiones

## 🤖 Agentes del Sistema

### 1. MobilitoConversacional
- **Especialidad**: Consultas generales y atención al cliente
- **Funciones**: Saludos, información bancaria básica, navegación de servicios
- **Personalidad**: Amigable, cálido y profesional

## 🚀 Instalación

### Prerrequisitos

- Python 3.8+
- Cuenta de Azure con acceso a Azure AI Foundry
- Azure AI Agents habilitado
- Azure AI Content Safety (opcional)

### Dependencias

```bash
pip install -r requirements.txt
```

### Dependencias incluidas:
```
azure-ai-agents>=1.0.0
azure-identity>=1.15.0
python-dotenv>=1.0.0
azure-ai-contentsafety>=1.0.0
azure-ai-inference>=1.0.0
azure-monitor-opentelemetry>=1.2.0
opentelemetry-api>=1.21.0
opentelemetry-sdk>=1.21.0
```

## ⚙️ Configuración

### 1. Variables de Entorno

Crea un archivo `.env` basado en el template:

```bash
# Azure AI Agents Configuration
PROJECT_ENDPOINT=https://tu-proyecto.services.ai.azure.com/api/projects/TuProyecto
MODEL_DEPLOYMENT_NAME=gpt-4

# Content Safety (opcional)
CONTENT_SAFETY_ENDPOINT=https://tu-content-safety.cognitiveservices.azure.com/

# Application Insights (opcional)
APPLICATION_INSIGHTS_CONNECTION_STRING=InstrumentationKey=tu-key;IngestionEndpoint=https://tu-region.in.applicationinsights.azure.com/
```

### 2. Autenticación Azure

El sistema usa `DefaultAzureCredential`. Configura una de estas opciones:

- **Azure CLI**: `az login`
- **Variables de entorno**:
  ```bash
  AZURE_CLIENT_ID=tu-client-id
  AZURE_CLIENT_SECRET=tu-client-secret
  AZURE_TENANT_ID=tu-tenant-id
  ```
- **Managed Identity** (en Azure)

## 🎯 Uso

### 1. Crear el Sistema de Agentes

```bash
python3 crear_agente.py
```

Este comando:
- Crea los tres agentes especializados
- Configura herramientas de orquestación
- Guarda los IDs en variables de entorno
- Muestra un resumen del sistema

### 2. Iniciar Conversación

```bash
python3 basic-agent.py
```

Este comando:
- Carga el agente orquestador
- Inicia el chat interactivo
- Aplica moderación de contenido
- Registra métricas de tracing

### 3. Comandos de Chat

- **Conversar**: Escribe cualquier mensaje
- **Salir**: `salir`, `quit`, `exit`, `bye`, `adiós`

## 📊 Monitoreo y Tracing

### Métricas Capturadas

- **Duración de ejecuciones**: Tiempo de respuesta de agentes
- **Moderación de contenido**: Resultados de análisis de seguridad
- **Intercambios conversacionales**: Métricas de sesión
- **Orquestación**: Decisiones de derivación

### Visualización

Si configuraste Application Insights, las métricas aparecen en:
- Azure Portal > Application Insights > Rendimiento
- Consultas personalizadas con KQL
- Dashboards de Azure Monitor

## 🔒 Seguridad

### Moderación de Contenido

- **Análisis bidireccional**: Entrada del usuario y respuestas del agente
- **Categorías monitoreadas**: Odio, violencia, contenido sexual, autolesiones
- **Umbrales configurables**: Severidad 0-7 (bloqueo por defecto en 4+)
- **Logging detallado**: Registro de todos los eventos de moderación

### Mejores Prácticas

- Variables de entorno para credenciales
- Autenticación con Azure AD
- Logging de eventos de seguridad
- Validación de entrada

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Usuario       │    │  MobilitoOrques  │    │  Especialistas  │
│                 │    │     tador        │    │                 │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ • Chat input    │───▶│ • Análisis       │───▶│ • Conversacional│
│ • Comandos      │    │ • Clasificación  │    │ • Tarjetas      │
│ • Visualización │◀───│ • Orquestación   │◀───│ • Respuestas    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Content Safety  │    │ OpenTelemetry    │    │ Azure Monitor   │
│ • Moderación    │    │ • Tracing        │    │ • Métricas      │
│ • Análisis      │    │ • Spans          │    │ • Dashboards    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📁 Estructura del Proyecto

```
agent-client/
├── basic-agent.py          # Aplicación principal de chat
├── crear_agente.py         # Gestión del sistema de agentes
├── requirements.txt        # Dependencias Python
├── .env                   # Variables de entorno (crear)
├── .env.example          # Template de configuración
└── README.md             # Esta documentación
```

## 🔧 Desarrollo

### Agregar Nuevos Agentes

1. Actualiza `definiciones_agentes` en `crear_agente.py`
2. Define especialidad e instrucciones
3. Configura herramientas si es necesario
4. Agrega variable de entorno correspondiente

### Personalizar Herramientas

1. Modifica `herramientas_orquestacion`
2. Define parámetros y descripción
3. Actualiza instrucciones del orquestador
4. Implementa lógica de manejo si es necesario

### Extender Moderación

1. Ajusta umbrales en `moderar_texto()`
2. Personaliza categorías analizadas
3. Modifica acciones para contenido flagged
4. Agrega logging personalizado

## 🐛 Solución de Problemas

### Error: "No module named 'azure.ai.agents'"

```bash
pip install azure-ai-agents azure-identity
```

### Error: "AGENT_ID not found"

1. Ejecuta `python3 crear_agente.py` primero
2. Verifica que `.env` contiene los IDs de agentes
3. Recarga variables de entorno si es necesario

### Error: "Authentication failed"

1. Ejecuta `az login` para Azure CLI
2. Verifica credenciales en variables de entorno
3. Confirma permisos en Azure AI Foundry

### Agentes no responden

1. Verifica que MODEL_DEPLOYMENT_NAME es correcto
2. Confirma que el modelo está desplegado
3. Revisa logs de Azure AI Foundry

## 📝 Ejemplos de Uso

### Consulta General
```
Tú: Hola, ¿qué servicios bancarios ofrecen?
Agente: ¡Hola! Te voy a conectar con nuestro especialista en información general...
[Deriva a MobilitoConversacional]
```

