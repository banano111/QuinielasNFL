#!/usr/bin/env python3.10
"""
Script de inicialización para QuinielasApp en PythonAnywhere
Ejecutar una sola vez después de subir los archivos
"""

import os
import sys
import sqlite3
import hashlib
from datetime import datetime

def print_step(step, message):
    """Imprimir paso con formato"""
    print(f"\n{'='*50}")
    print(f"PASO {step}: {message}")
    print(f"{'='*50}")

def create_database():
    """Crear todas las tablas de la base de datos"""
    print_step(1, "CREANDO BASE DE DATOS Y TABLAS")
    
    # Conectar a la base de datos (se crea si no existe)
    conn = sqlite3.connect('quiniela.db')
    cursor = conn.cursor()
    
    # Crear tabla users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Tabla 'users' creada")
    
    # Crear tabla picks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game_id TEXT,
            team_picked TEXT,
            week INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    print("✅ Tabla 'picks' creada")
    
    # Crear tabla game_results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT UNIQUE,
            week INTEGER,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            winner TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Tabla 'game_results' creada")
    
    # Crear tabla system_config
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Tabla 'system_config' creada")
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente")

def create_admin_user():
    """Crear usuario administrador"""
    print_step(2, "CREANDO USUARIO ADMINISTRADOR")
    
    conn = sqlite3.connect('quiniela.db')
    cursor = conn.cursor()
    
    # Verificar si ya existe admin
    cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone():
        print("⚠️  Usuario admin ya existe, saltando creación")
    else:
        # Crear hash de contraseña
        password = 'QuinielasNFL2024!'
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        # Insertar admin
        cursor.execute('''
            INSERT INTO users (username, password, is_admin)
            VALUES (?, ?, ?)
        ''', ('admin', password_hash, 1))
        
        print("✅ Usuario administrador creado")
        print(f"   Usuario: admin")
        print(f"   Contraseña: {password}")
    
    conn.commit()
    conn.close()

def init_system_config():
    """Inicializar configuración del sistema"""
    print_step(3, "CONFIGURANDO SISTEMA")
    
    conn = sqlite3.connect('quiniela.db')
    cursor = conn.cursor()
    
    configs = [
        ('current_week', '4'),
        ('picks_locked', '0'),
        ('season_year', '2024')
    ]
    
    for key, value in configs:
        cursor.execute('''
            INSERT OR REPLACE INTO system_config (config_key, config_value, updated_at)
            VALUES (?, ?, ?)
        ''', (key, value, datetime.now()))
        print(f"✅ Configuración '{key}' = '{value}'")
    
    conn.commit()
    conn.close()

def verify_installation():
    """Verificar que todo esté instalado correctamente"""
    print_step(4, "VERIFICANDO INSTALACIÓN")
    
    # Verificar archivos
    required_files = ['app.py', 'wsgi.py', 'templates/']
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} existe")
        else:
            print(f"❌ {file} NO ENCONTRADO")
            return False
    
    # Verificar base de datos
    if os.path.exists('quiniela.db'):
        print("✅ Base de datos creada")
    else:
        print("❌ Base de datos NO creada")
        return False
    
    # Verificar tablas
    conn = sqlite3.connect('quiniela.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = ['users', 'picks', 'game_results', 'system_config']
    for table in required_tables:
        if table in tables:
            print(f"✅ Tabla '{table}' existe")
        else:
            print(f"❌ Tabla '{table}' NO existe")
            return False
    
    # Verificar usuario admin
    cursor.execute('SELECT username, is_admin FROM users WHERE username = ?', ('admin',))
    admin = cursor.fetchone()
    if admin and admin[1] == 1:
        print("✅ Usuario administrador configurado")
    else:
        print("❌ Usuario administrador NO configurado")
        return False
    
    conn.close()
    return True

def test_import():
    """Probar que la aplicación se puede importar"""
    print_step(5, "PROBANDO IMPORTACIÓN DE LA APP")
    
    try:
        # Agregar directorio actual al path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Intentar importar la app
        from app import app
        print("✅ Aplicación Flask importada correctamente")
        return True
    except Exception as e:
        print(f"❌ Error al importar la aplicación: {e}")
        return False

def main():
    """Función principal"""
    print("🏈 INICIALIZADOR DE QUINIELAS APP")
    print("=" * 50)
    
    try:
        # Cambiar al directorio del script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        print(f"📁 Directorio de trabajo: {script_dir}")
        
        # Ejecutar pasos de inicialización
        create_database()
        create_admin_user()
        init_system_config()
        
        # Verificar instalación
        if verify_installation():
            print_step("✅", "VERIFICACIÓN EXITOSA")
        else:
            print_step("❌", "VERIFICACIÓN FALLÓ")
            return False
        
        # Probar importación
        if test_import():
            print_step("🎉", "INICIALIZACIÓN COMPLETA")
            print("\n🚀 PRÓXIMOS PASOS:")
            print("1. Ve a tu dashboard de PythonAnywhere")
            print("2. En la pestaña 'Web', click 'Reload banano111.pythonanywhere.com'")
            print("3. Accede a: https://banano111.pythonanywhere.com")
            print("4. Login con: admin / QuinielasNFL2024!")
            print("\n✨ ¡Tu aplicación está lista!")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)