# Quinielas NFL - Versión 2.0 con PostgreSQL y Peewee ORM

## 🏈 Sistema de Quinielas de la NFL

Aplicación web completa para gestionar quinielas de la NFL con sistema multi-liga, panel administrativo y integración con la API de ESPN.

## 🚀 Características

- ✅ **Autenticación de usuarios** - Registro, login, gestión de sesiones
- ✅ **Sistema multi-liga** - Los usuarios pueden unirse a múltiples ligas
- ✅ **Panel administrativo completo** - Gestión de ligas, usuarios y resultados
- ✅ **Integración ESPN API** - Datos en tiempo real de los juegos de NFL
- ✅ **PostgreSQL + Peewee ORM** - Base de datos robusta y ORM moderno
- ✅ **Interface HTMX** - Actualizaciones dinámicas sin recargar página
- ✅ **Docker para desarrollo** - PostgreSQL containerizado
- ✅ **Deploy en Render** - Configuración lista para producción

## 🏗️ Arquitectura Técnica

### Backend
- **Flask 3.0** - Framework web moderno
- **Peewee ORM** - Object-Relational Mapping ligero y potente
- **PostgreSQL** - Base de datos de producción
- **HTMX** - Interactividad dinámica
- **Gunicorn** - Servidor WSGI para producción

### Estructura del Proyecto
```
QuinielasNFL/
├── app.py                    # Aplicación principal Flask
├── config.py                 # Configuración del proyecto
├── migrate.py               # Script de migración de datos
├── requirements.txt         # Dependencias Python
├── docker-compose.yml       # PostgreSQL local
├── templates/               # Templates HTML
├── quinielasapp/           # Módulos de la aplicación
│   ├── models/             # Modelos de base de datos
│   └── services/           # Lógica de negocio
└── RENDER_DEPLOY.md        # Instrucciones de deploy
```

## 🔧 Configuración Local

### 1. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar PostgreSQL Local
```bash
# Iniciar PostgreSQL con Docker
docker-compose up -d

# Verificar que esté corriendo
docker ps
```

### 3. Configurar Variables de Entorno
```bash
cp .env.example .env
# Editar .env con tu configuración
```

### 4. Migrar Base de Datos
```bash
# Crear tablas y migrar datos (si existe SQLite)
python migrate.py
```

### 5. Ejecutar Aplicación
```bash
python app.py
```

La aplicación estará disponible en: `http://localhost:8000`

## 🎮 Uso de la Aplicación

### Usuario Regular
1. **Registro** - Crear cuenta con código de liga
2. **Hacer Picks** - Seleccionar ganadores para cada juego
3. **Ver Standings** - Consultar clasificación en tiempo real
4. **Cambiar Liga** - Alternar entre múltiples ligas

### Administrador
- **Gestión de Ligas** - Crear, editar, activar/desactivar ligas
- **Gestión de Usuarios** - Ver usuarios, agregar/remover de ligas
- **Procesar Resultados** - Actualizar resultados desde ESPN API
- **Declarar Ganadores** - Determinar ganadores semanales
- **Estadísticas** - Dashboard completo del sistema

## 🗄️ Modelos de Base de Datos

### User
- Información del usuario, contraseña hasheada, privilegios admin

### League  
- Ligas con código único, descripción, límites de miembros

### LeagueMembership
- Relación usuarios-ligas con estado activo

### Pick
- Selecciones de usuarios para juegos específicos por semana

### GameResult
- Resultados oficiales de juegos con puntajes

### SystemConfig
- Configuración global (semana actual, bloqueo de picks)

## 🔌 Integraciones

### ESPN API
- Obtención automática de juegos y resultados
- Fallback a datos mock si la API falla
- Procesamiento automático de ganadores

### PostgreSQL
- Base de datos de producción
- Soporte para múltiples conexiones concurrentes  
- Backup y recovery automático en Render

## 🚀 Deploy en Producción

### Render.com (Recomendado)
1. **Crear PostgreSQL Service**
2. **Crear Web Service** conectado al repo
3. **Configurar variables de entorno**
4. **Deploy automático** con git push

Ver: [RENDER_DEPLOY.md](RENDER_DEPLOY.md) para instrucciones detalladas

### Variables de Entorno Requeridas
```bash
FLASK_ENV=production
SECRET_KEY=your-super-secure-key
DATABASE_URL=postgresql://... # Auto-configurado por Render
```

## 🔒 Seguridad

- ✅ Contraseñas hasheadas con SHA-256
- ✅ Sesiones Flask seguras
- ✅ Validación de privilegios admin
- ✅ Sanitización de inputs
- ✅ Variables de entorno para secretos

## 🧪 Testing Local

### Verificar PostgreSQL
```bash
# Conectar con Adminer (opcional)
# http://localhost:8080
# Sistema: PostgreSQL
# Servidor: postgres  
# Usuario: postgres
# Contraseña: dev_password123
# Base de datos: quiniela_dev
```

### Verificar Aplicación
```bash
# Crear liga de prueba (como admin)
# Login: admin / QuinielasNFL2024!
# Panel Admin > Crear Liga

# Registro de usuario de prueba
# Usar código de liga creado arriba
```

## 🔄 Migración desde SQLite

El script `migrate.py` automáticamente:
1. **Detecta** base de datos SQLite existente
2. **Migra** todos los datos a PostgreSQL  
3. **Preserva** usuarios, ligas, picks y configuración
4. **Crea** administrador por defecto si no existe

## 📈 Monitoreo y Logs

### Render Dashboard
- Logs en tiempo real
- Métricas de rendimiento  
- Estado de base de datos
- Variables de entorno

### Logs Locales
- Errores de conexión a PostgreSQL
- Problemas con ESPN API
- Errores de autenticación
- Debugging de queries

## 🛠️ Desarrollo

### Estructura de Código
- **Models** - Definición de tablas con Peewee
- **Services** - Lógica de negocio reutilizable
- **Routes** - Endpoints de la aplicación Flask
- **Templates** - HTML con integración HTMX

### Mejores Prácticas
- Usar transacciones para operaciones críticas
- Validar datos de entrada
- Manejar errores graciosamente
- Documentar funciones complejas

## 📞 Soporte

Para problemas o mejoras:
1. Revisar logs de la aplicación
2. Verificar variables de entorno
3. Comprobar estado de PostgreSQL
4. Consultar documentación de Render

---

## 🎉 ¡La aplicación está lista!

**Tecnologías:** Flask 3.0 + Peewee ORM + PostgreSQL + HTMX + Docker + Render
**Estado:** ✅ Migración completa - Lista para producción