import os
from peewee import *
import sqlite3

# Intentar importar PostgreSQL drivers
try:
    import psycopg2
    from playhouse.postgres_ext import PostgresqlExtDatabase
    POSTGRES_AVAILABLE = True
except ImportError:
    try:
        from playhouse.pool import PooledPostgresqlDatabase as PostgresqlDatabase
        POSTGRES_AVAILABLE = True
    except ImportError:
        POSTGRES_AVAILABLE = False

# Configuración de base de datos
config_name = os.environ.get('FLASK_ENV', 'development')

if os.environ.get('USE_SQLITE', 'False').lower() == 'true':
    # SQLite para desarrollo rápido
    database = SqliteDatabase(os.environ.get('SQLITE_PATH', 'quiniela.db'))
else:
    # PostgreSQL para desarrollo y producción
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and POSTGRES_AVAILABLE:
        # Producción (Render) - usa DATABASE_URL
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        try:
            # Parse DATABASE_URL para extraer componentes
            from urllib.parse import urlparse
            result = urlparse(database_url)
            database = PostgresqlDatabase(
                result.path[1:],  # nombre de la base de datos (sin el / inicial)
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port or 5432,
                autoconnect=False  # No conectar automáticamente
            )
        except Exception as e:
            print(f"Error configurando PostgreSQL: {e}")
            # Fallback a SQLite si PostgreSQL falla
            database = SqliteDatabase('fallback.db')
    elif not database_url and POSTGRES_AVAILABLE:
        # Desarrollo local - usa variables individuales
        try:
            database = PostgresqlDatabase(
                os.environ.get('DB_NAME', 'quiniela_dev'),
                user=os.environ.get('DB_USER', 'postgres'),
                password=os.environ.get('DB_PASSWORD', 'dev_password123'),
                host=os.environ.get('DB_HOST', 'localhost'),
                port=int(os.environ.get('DB_PORT', '5432')),
                autoconnect=False
            )
        except Exception as e:
            print(f"Error configurando PostgreSQL local: {e}")
            database = SqliteDatabase('local_fallback.db')
    else:
        # Fallback a SQLite si PostgreSQL no está disponible
        print("PostgreSQL no disponible, usando SQLite")
        database = SqliteDatabase('quiniela_fallback.db')

class BaseModel(Model):
    class Meta:
        database = database