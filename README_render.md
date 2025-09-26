# QuinielasApp - NFL Picks Application

Aplicación web para quinelas de la NFL usando Flask.

## Características

- Sistema de usuarios con autenticación
- Quinelas semanales de la NFL
- Integración con API de ESPN para datos reales
- Panel de administración
- Interfaz responsive con Tailwind CSS

## Deploy en Render

### Configuración automática:
- **Build Command**: `./build.sh`
- **Start Command**: `gunicorn -c gunicorn.conf.py app:app`
- **Environment**: Python 3

### Variables de entorno (opcional):
- `ENVIRONMENT=production`

## Instalación Local

1. Clona el repositorio
2. Instala dependencias: `pip install -r requirements.txt`
3. Ejecuta: `python app.py`
4. Accede a `http://localhost:5000`

## Configuración de Seguridad

- Contraseña de admin por defecto: `QuinielasNFL2024!` (cámbiala después del primer login)
- La base de datos se inicializa automáticamente

## Uso

- Accede a `/admin` para configurar semanas y bloquear picks
- Los usuarios pueden registrarse y hacer sus picks semanales
- Los resultados se actualizan automáticamente desde ESPN

## Tecnologías

- Flask 3.0.0
- SQLite
- HTMX
- Tailwind CSS
- ESPN API
- Gunicorn (producción)