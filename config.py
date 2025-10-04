import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    DB_NAME = os.environ.get('DB_NAME', 'quiniela')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'password')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', '5432'))
    
    # Para desarrollo local con SQLite (fallback)
    USE_SQLITE = os.environ.get('USE_SQLITE', 'False').lower() == 'true'
    SQLITE_PATH = os.environ.get('SQLITE_PATH', 'quiniela.db')

class DevelopmentConfig(Config):
    DEBUG = True
    # Usar PostgreSQL por defecto en desarrollo también
    USE_SQLITE = os.environ.get('USE_SQLITE', 'False').lower() == 'true'

class ProductionConfig(Config):
    DEBUG = False
    
    # Render automáticamente provee DATABASE_URL para PostgreSQL
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    if database_url:
        # Parse DATABASE_URL para extraer componentes
        from urllib.parse import urlparse
        result = urlparse(database_url)
        DB_NAME = result.path[1:]
        DB_USER = result.username
        DB_PASSWORD = result.password
        DB_HOST = result.hostname
        DB_PORT = result.port or 5432

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}