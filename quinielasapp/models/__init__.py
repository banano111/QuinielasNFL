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
    # Producción (Render) - configurar PostgreSQL con pg8000 forzado
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print(f"🔗 Conectando a: {database_url.split('@')[1] if '@' in database_url else 'PostgreSQL'}")
    
    # Parse DATABASE_URL
    result = urlparse(database_url)
    
    # Crear clase personalizada que fuerza el uso de pg8000
    class Pg8000PostgresDatabase(PostgresqlDatabase):
        def _connect(self):
            # Forzar el uso de pg8000 directamente
            import pg8000.dbapi
            
            # Usar los atributos correctos de Peewee
            conn_params = {
                'host': getattr(self, 'host', 'localhost'),
                'port': getattr(self, 'port', 5432),
                'user': getattr(self, 'user', None),
                'password': getattr(self, 'password', None),
                'database': self.database
            }
            
            # Agregar parámetros adicionales de connect_params si existen
            if hasattr(self, 'connect_params'):
                conn_params.update(self.connect_params)
            
            # Remover None values
            conn_params = {k: v for k, v in conn_params.items() if v is not None}
            
            print(f"📡 Conectando con pg8000 a {conn_params.get('host')}:{conn_params.get('port')}")
            
            conn = pg8000.dbapi.connect(**conn_params)
            
            # Agregar server_version manualmente para compatibilidad con Peewee
            if not hasattr(conn, 'server_version'):
                try:
                    # Obtener versión del servidor
                    cursor = conn.cursor()
                    cursor.execute("SELECT version()")
                    version_str = cursor.fetchone()[0]
                    cursor.close()
                    
                    # Extraer número de versión (ej: "PostgreSQL 14.9" -> 140009)
                    import re
                    match = re.search(r'PostgreSQL (\d+)\.(\d+)', version_str)
                    if match:
                        major, minor = match.groups()
                        conn.server_version = int(major) * 10000 + int(minor) * 100
                    else:
                        conn.server_version = 130000  # Default fallback
                        
                    print(f"🔢 Server version detectada: {conn.server_version}")
                except Exception as e:
                    print(f"⚠️ No se pudo obtener server_version: {e}")
                    conn.server_version = 130000  # Default fallback
            
            return conn
    
    # Crear instancia con configuración manual
    database = Pg8000PostgresDatabase(
        result.path[1:],  # database name
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port or 5432,
        autoconnect=False
    )
    print("✅ Base de datos configurada con pg8000 forzado")
    
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