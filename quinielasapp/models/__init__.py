import os
from peewee import *
from playhouse.postgres_ext import PostgresqlExtDatabase
import sqlite3

# Configuración de base de datos
config_name = os.environ.get('FLASK_ENV', 'development')

if os.environ.get('USE_SQLITE', 'False').lower() == 'true':
    # SQLite para desarrollo rápido
    database = SqliteDatabase(os.environ.get('SQLITE_PATH', 'quiniela.db'))
else:
    # PostgreSQL para desarrollo y producción
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Producción (Render) - usa DATABASE_URL
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        database = PostgresqlDatabase(database_url)
    else:
        # Desarrollo local - usa variables individuales
        database = PostgresqlDatabase(
            os.environ.get('DB_NAME', 'quiniela_dev'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', 'dev_password123'),
            host=os.environ.get('DB_HOST', 'localhost'),
            port=int(os.environ.get('DB_PORT', '5432'))
        )

class BaseModel(Model):
    class Meta:
        database = database