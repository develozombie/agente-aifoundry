#!/usr/bin/env python3
"""
MCP Server para chistes de Chuck Norris.
Este servidor proporciona herramientas para obtener chistes aleatorios de Chuck Norris
utilizando la API de https://api.chucknorris.io/
"""

import asyncio
import logging
from typing import Any, Dict, List

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.types import Image
from mcp import types

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear el servidor MCP
mcp = FastMCP("Chuck Norris Jokes Server")

# URL base de la API de Chuck Norris
CHUCK_NORRIS_API_BASE = "https://api.chucknorris.io/jokes"

@mcp.tool()
async def get_random_joke() -> str:
    """
    Obtiene un chiste aleatorio de Chuck Norris.
    
    Returns:
        str: Un chiste aleatorio de Chuck Norris
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CHUCK_NORRIS_API_BASE}/random")
            response.raise_for_status()
            
            joke_data = response.json()
            return joke_data.get("value", "No se pudo obtener el chiste")
            
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP al obtener chiste: {e}")
        return f"Error al conectar con la API: {e}"
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return f"Error inesperado: {e}"

@mcp.tool()
async def get_joke_categories() -> List[str]:
    """
    Obtiene las categorías disponibles de chistes de Chuck Norris.
    
    Returns:
        List[str]: Lista de categorías disponibles
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CHUCK_NORRIS_API_BASE}/categories")
            response.raise_for_status()
            
            categories = response.json()
            return categories if isinstance(categories, list) else []
            
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP al obtener categorías: {e}")
        return [f"Error al conectar con la API: {e}"]
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return [f"Error inesperado: {e}"]

@mcp.tool()
async def get_joke_by_category(category: str) -> str:
    """
    Obtiene un chiste aleatorio de Chuck Norris de una categoría específica.
    
    Args:
        category: La categoría del chiste (ej: "dev", "animal", "career", etc.)
    
    Returns:
        str: Un chiste de Chuck Norris de la categoría especificada
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CHUCK_NORRIS_API_BASE}/random", 
                                      params={"category": category})
            response.raise_for_status()
            
            joke_data = response.json()
            return joke_data.get("value", "No se pudo obtener el chiste")
            
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP al obtener chiste por categoría: {e}")
        return f"Error al conectar con la API: {e}"
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return f"Error inesperado: {e}"

@mcp.tool()
async def search_jokes(query: str) -> List[Dict[str, Any]]:
    """
    Busca chistes de Chuck Norris que contengan una palabra o frase específica.
    
    Args:
        query: La palabra o frase a buscar en los chistes
    
    Returns:
        List[Dict[str, Any]]: Lista de chistes que coinciden con la búsqueda
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CHUCK_NORRIS_API_BASE}/search", 
                                      params={"query": query})
            response.raise_for_status()
            
            search_data = response.json()
            jokes = search_data.get("result", [])
            
            # Formatear los resultados para que sean más legibles
            formatted_jokes = []
            for joke in jokes[:5]:  # Limitar a 5 resultados
                formatted_jokes.append({
                    "joke": joke.get("value", ""),
                    "id": joke.get("id", ""),
                    "url": joke.get("url", ""),
                    "categories": joke.get("categories", [])
                })
            
            return formatted_jokes
            
    except httpx.HTTPError as e:
        logger.error(f"Error HTTP al buscar chistes: {e}")
        return [{"error": f"Error al conectar con la API: {e}"}]
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return [{"error": f"Error inesperado: {e}"}]

@mcp.resource("chuck-norris://info")
def get_api_info() -> str:
    """
    Proporciona información sobre la API de Chuck Norris y cómo usar este servidor.
    """
    return """
# Chuck Norris Jokes MCP Server

Este servidor MCP proporciona acceso a la API de chistes de Chuck Norris (https://api.chucknorris.io/).

## Herramientas Disponibles:

1. **get_random_joke()**: Obtiene un chiste aleatorio de Chuck Norris
2. **get_joke_categories()**: Lista todas las categorías disponibles de chistes
3. **get_joke_by_category(category)**: Obtiene un chiste de una categoría específica
4. **search_jokes(query)**: Busca chistes que contengan una palabra o frase específica

## Categorías Populares:
- dev (desarrollo/programación)
- animal
- career
- celebrity
- explicit
- fashion
- food
- history
- money
- movie
- music
- political
- religion
- science
- sport
- travel

## Ejemplo de Uso:
- Para obtener un chiste aleatorio: usa get_random_joke()
- Para chistes de programación: usa get_joke_by_category("dev")
- Para buscar chistes sobre "computer": usa search_jokes("computer")
"""

# Función principal para ejecutar el servidor
def main():
    """Función principal para ejecutar el servidor MCP."""
    logger.info("Iniciando Chuck Norris Jokes MCP Server...")
    mcp.run()

if __name__ == "__main__":
    main()