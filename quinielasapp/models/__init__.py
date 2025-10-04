import os
from urllib.parse import urlparse

# Importar pg8000 y Peewee con soporte explícito
try:
    import pg8000
    PG8000_AVAILABLE = True
    print("✅ pg8000 importado correctamente")
except ImportError:
    PG8000_AVAILABLE = False
    print("❌ pg8000 no disponible")

from peewee import *

# Solo PostgreSQL con pg8000
print("🐘 Configurando PostgreSQL con pg8000...")

# Configuración de base de datos - Solo PostgreSQL
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # Producción (Render) - usar DATABASE_URL con pg8000
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print(f"🔗 Conectando a: {database_url.split('@')[1] if '@' in database_url else 'PostgreSQL'}")
    
    # Usar el DATABASE_URL directamente - Peewee debería detectar pg8000 automáticamente
    from playhouse.db_url import connect
    try:
        database = connect(database_url)
        print("✅ Conexión PostgreSQL configurada con playhouse.db_url")
    except Exception as e:
        print(f"❌ Error con playhouse.db_url: {e}")
        # Fallback manual
        result = urlparse(database_url)
        database = PostgresqlDatabase(
            result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port or 5432,
            autoconnect=False
        )
        print("✅ Configuración PostgreSQL manual lista")
    
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