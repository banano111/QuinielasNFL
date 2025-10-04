import os
from peewee import *
from urllib.parse import urlparse

# Solo PostgreSQL con pg8000
print("🐘 Configurando PostgreSQL con pg8000...")

# Configuración de base de datos - Solo PostgreSQL
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # Producción (Render) - usar DATABASE_URL con pg8000
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print(f"🔗 Conectando a: {database_url.split('@')[1] if '@' in database_url else 'PostgreSQL'}")
    
    # Parse DATABASE_URL para extraer componentes
    result = urlparse(database_url)
    database = PostgresqlDatabase(
        result.path[1:],  # nombre de la base de datos (sin el / inicial)
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port or 5432,
        autoconnect=False,
        # Especificar pg8000 como driver
        options={'sslmode': 'prefer'}
    )
    print("✅ Configuración PostgreSQL con pg8000 lista")
    
else:
    # Desarrollo local - usar variables individuales
    database = PostgresqlDatabase(
        os.environ.get('DB_NAME', 'quiniela_dev'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'dev_password123'),
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', '5432')),
        autoconnect=False,
        options={'sslmode': 'prefer'}
    )
    print("✅ Configuración PostgreSQL local lista")

class BaseModel(Model):
    class Meta:
        database = database