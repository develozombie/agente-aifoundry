#!/usr/bin/env python3
"""
Script para probar el servidor MCP de Chuck Norris localmente.
"""

import asyncio
import json
from chuck_norris_server import get_random_joke, get_joke_categories, get_joke_by_category, search_jokes

async def test_server():
    """Prueba todas las funciones del servidor MCP."""
    print("🥊 Probando el servidor MCP de Chuck Norris...")
    print("=" * 50)
    
    # Probar chiste aleatorio
    print("\n1. Chiste aleatorio:")
    joke = await get_random_joke()
    print(f"   {joke}")
    
    # Probar categorías
    print("\n2. Categorías disponibles:")
    categories = await get_joke_categories()
    print(f"   {', '.join(categories)}")
    
    # Probar chiste por categoría
    if categories and 'dev' in categories:
        print("\n3. Chiste de programación:")
        dev_joke = await get_joke_by_category("dev")
        print(f"   {dev_joke}")
    
    # Probar búsqueda
    print("\n4. Búsqueda de chistes con 'computer':")
    search_results = await search_jokes("computer")
    if search_results:
        for i, result in enumerate(search_results[:2], 1):
            if 'joke' in result:
                print(f"   {i}. {result['joke']}")
    
    print("\n" + "=" * 50)
    print("✅ Pruebas completadas!")

if __name__ == "__main__":
    asyncio.run(test_server())