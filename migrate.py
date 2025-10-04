#!/usr/bin/env python3
"""
Script de migración e inicialización de base de datos PostgreSQL.
Crea las tablas e inicializa la configuración del sistema.
"""

import os
import sys
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DevelopmentConfig
from quinielasapp.models import database
from quinielasapp.models.models import *
from quinielasapp.services.database_service import create_default_admin, initialize_system_config

def create_all_tables():
    """Crea todas las tablas en PostgreSQL"""
    print("Creando tablas...")
    
    # Crear todas las tablas
    database.create_tables([
        User,
        League, 
        LeagueMembership,
        Pick,
        GameResult,
        WinnersHistory,
        SystemConfig
    ], safe=True)  # safe=True no da error si ya existen
    
    print("✅ Tablas creadas exitosamente")

def check_existing_data():
    """Verificar si ya hay datos en PostgreSQL"""
    try:
        user_count = User.select().count()
        if user_count > 0:
            print(f"📊 Base de datos ya tiene {user_count} usuarios")
            return True
        return False
    except Exception as e:
        print(f"⚠️ Error verificando datos existentes: {e}")
        return False

def initialize_fresh_db():
    """Inicializa una base de datos completamente nueva"""
    print("🆕 Inicializando base de datos nueva...")
    
    # Crear usuario admin por defecto
    admin = create_default_admin()
    print(f"✅ Admin creado: {admin.username}")
    
    # Configuración inicial
    initialize_system_config()
    print("✅ Configuración inicial creada")

def main():
    """Función principal de migración"""
    print("🚀 Iniciando migración de base de datos...")
    print(f"🔗 Conectando a PostgreSQL...")
    
    # Asegurar conexión
    try:
        database.connect()
        print("✅ Conexión a PostgreSQL exitosa")
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        print("💡 Asegúrate de que Docker esté corriendo: docker-compose up -d")
        return
    
    # Crear tablas
    create_all_tables()
    
    # Verificar si hay datos existentes
    if check_existing_data():
        print("⏭️ Saltando inicialización - datos ya existen")
    else:
        # Inicializar base de datos desde cero
        initialize_fresh_db()
    
    print("🎉 ¡Migración completada!")
    print("\n📋 Próximos pasos:")
    print("  1. Verificar datos en Adminer: http://localhost:8080")
    print("     - Sistema: PostgreSQL")
    print("     - Servidor: postgres")
    print("     - Usuario: postgres") 
    print("     - Contraseña: dev_password123")
    print("     - Base de datos: quiniela_dev")
    print("\n  2. Ejecutar la aplicación:")
    print("     python3 run.py")

if __name__ == "__main__":
    main()