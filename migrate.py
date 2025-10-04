#!/usr/bin/env python3
"""
Script de migración e inicialización de base de datos.
Crea las tablas y migra datos desde SQLite a PostgreSQL si es necesario.
"""

import os
import sys
import sqlite3
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

def migrate_from_sqlite():
    """Migra datos desde SQLite existente a PostgreSQL"""
    sqlite_path = 'quiniela.db'
    
    if not os.path.exists(sqlite_path):
        print(f"❌ No se encontró {sqlite_path}, saltando migración")
        return
    
    print(f"📦 Migrando datos desde {sqlite_path}...")
    
    # Conectar a SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
    
    try:
        # Migrar usuarios
        print("👥 Migrando usuarios...")
        users_cursor = sqlite_conn.execute('SELECT * FROM users ORDER BY id')
        for row in users_cursor:
            try:
                user = User.create(
                    username=row['username'],
                    password=row['password'],
                    first_name=row.get('first_name'),
                    last_name=row.get('last_name'),
                    is_admin=bool(row['is_admin']),
                    created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else datetime.now()
                )
                print(f"  ✅ Usuario: {user.username}")
            except Exception as e:
                print(f"  ⚠️ Error migrando usuario {row['username']}: {e}")
        
        # Migrar ligas
        print("🏆 Migrando ligas...")
        leagues_cursor = sqlite_conn.execute('SELECT * FROM leagues ORDER BY id')
        for row in leagues_cursor:
            try:
                creator = User.get(User.username == sqlite_conn.execute(
                    'SELECT username FROM users WHERE id = ?', (row['created_by'],)
                ).fetchone()[0])
                
                league = League.create(
                    name=row['name'],
                    code=row['code'],
                    description=row.get('description'),
                    created_by=creator,
                    is_active=bool(row['is_active']),
                    max_members=row.get('max_members', 50),
                    created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else datetime.now()
                )
                print(f"  ✅ Liga: {league.name}")
            except Exception as e:
                print(f"  ⚠️ Error migrando liga {row['name']}: {e}")
        
        # Migrar membresías
        print("👥 Migrando membresías...")
        memberships_cursor = sqlite_conn.execute('SELECT * FROM league_memberships ORDER BY id')
        for row in memberships_cursor:
            try:
                user_row = sqlite_conn.execute('SELECT username FROM users WHERE id = ?', (row['user_id'],)).fetchone()
                league_row = sqlite_conn.execute('SELECT code FROM leagues WHERE id = ?', (row['league_id'],)).fetchone()
                
                if user_row and league_row:
                    user = User.get(User.username == user_row[0])
                    league = League.get(League.code == league_row[0])
                    
                    membership = LeagueMembership.create(
                        user=user,
                        league=league,
                        joined_at=datetime.fromisoformat(row['joined_at']) if row.get('joined_at') else datetime.now(),
                        is_active=bool(row.get('is_active', 1))
                    )
                    print(f"  ✅ Membresía: {user.username} -> {league.name}")
            except Exception as e:
                print(f"  ⚠️ Error migrando membresía: {e}")
        
        # Migrar picks
        print("🏈 Migrando picks...")
        picks_cursor = sqlite_conn.execute('SELECT * FROM picks ORDER BY id')
        for row in picks_cursor:
            try:
                user_row = sqlite_conn.execute('SELECT username FROM users WHERE id = ?', (row['user_id'],)).fetchone()
                league_row = sqlite_conn.execute('SELECT code FROM leagues WHERE id = ?', (row['league_id'],)).fetchone()
                
                if user_row and league_row:
                    user = User.get(User.username == user_row[0])
                    league = League.get(League.code == league_row[0])
                    
                    pick = Pick.create(
                        user=user,
                        league=league,
                        week=row['week'],
                        game_id=row['game_id'],
                        selection=row['selection'],
                        created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else datetime.now()
                    )
                    print(f"  ✅ Pick: {user.username} - Semana {row['week']}")
            except Exception as e:
                print(f"  ⚠️ Error migrando pick: {e}")
        
        # Migrar resultados de juegos
        print("📊 Migrando resultados...")
        results_cursor = sqlite_conn.execute('SELECT * FROM game_results ORDER BY id')
        for row in results_cursor:
            try:
                result = GameResult.create(
                    week=row['week'],
                    game_id=row['game_id'],
                    winner=row['winner'],
                    home_team=row.get('home_team'),
                    away_team=row.get('away_team'),
                    home_score=row.get('home_score'),
                    away_score=row.get('away_score'),
                    updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else datetime.now()
                )
                print(f"  ✅ Resultado: Semana {row['week']} - {row['game_id']}")
            except Exception as e:
                print(f"  ⚠️ Error migrando resultado: {e}")
        
        # Migrar configuración del sistema
        print("⚙️ Migrando configuración...")
        config_cursor = sqlite_conn.execute('SELECT * FROM system_config ORDER BY id')
        for row in config_cursor:
            try:
                config = SystemConfig.create(
                    config_key=row['config_key'],
                    config_value=row['config_value'],
                    updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else datetime.now()
                )
                print(f"  ✅ Config: {row['config_key']} = {row['config_value']}")
            except Exception as e:
                print(f"  ⚠️ Error migrando config: {e}")
        
        print("✅ Migración completada exitosamente")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
    finally:
        sqlite_conn.close()

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
    user_count = User.select().count()
    
    if user_count > 0:
        print(f"📊 Base de datos ya tiene {user_count} usuarios")
        print("⏭️ Saltando inicialización")
    else:
        # Intentar migrar desde SQLite
        migrate_from_sqlite()
        
        # Si no hay datos después de la migración, inicializar desde cero
        if User.select().count() == 0:
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