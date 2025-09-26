# Quinielas NFL - Despliegue en PythonAnywhere# Quiniela NFL - App mínima (Flask + SQLite + HTMX + Tailwind)



## Preparación para Producción ✅Proyecto inicial para gestionar una quiniela semanal (registro, picks, clasificación).



### Cambios de Seguridad Aplicados:Requisitos:

- ✅ **Banner de admin removido** del login- Python 3.8+

- ✅ **Contraseña de admin cambiada** de `admin_pass` a `QuinielasNFL2024!`- Instalar dependencias: pip install -r requirements.txt

- ✅ **Debug mode** preparado para producción

- ✅ **Auto-refresh removido** para optimizar llamadas al APIArrancar la app:



### Credenciales de Administrador:1. Crear/activar un entorno virtual

```2. pip install -r requirements.txt

Usuario: admin3. python app.py

Contraseña: QuinielasNFL2024!

```La app creará `quiniela.db` en la carpeta del proyecto y sembrará algunos partidos de ejemplo.



## Instrucciones de Despliegue en PythonAnywhereRutas principales:

- /register - crear usuario

### 1. Crear Cuenta en PythonAnywhere- /login - iniciar sesión

- Ir a [pythonanywhere.com](https://www.pythonanywhere.com)- /picks - formulario de picks (usa HTMX para enviar)

- Crear una cuenta gratuita- /standings - ver clasificación (fragmento HTMX)

- /simulate_results - simula resultados aleatorios (POST via HTMX)

### 2. Subir Archivos

```bashNotas:

# En la consola de PythonAnywhere:- Cambia la variable `app.secret_key` por una cadena segura en producción.

git clone https://github.com/tuusuario/QuinielasApp.git- Tailwind se incluye vía CDN para prototipado rápido; considera compilar en producción.

# O subir archivos manualmente via Files tab
```

### 3. Instalar Dependencias
```bash
pip3.10 install --user -r requirements.txt
```

### 4. Configurar WSGI
- En el dashboard de PythonAnywhere, ir a "Web"
- Crear una nueva web app (Python 3.10, Flask)
- Editar el archivo WSGI y reemplazar con el contenido de `wsgi.py`
- Cambiar `tuusuario` por tu username real

### 5. Configurar Base de Datos
- La base de datos SQLite se creará automáticamente en el primer acceso
- Los datos se almacenan en `/home/tuusuario/QuinielasApp/quinielas.db`

### 6. Configurar Archivos Estáticos
- En la pestaña "Static files" del dashboard:
  - URL: `/static/`
  - Directory: `/home/tuusuario/QuinielasApp/static/`

### 7. Variables de Entorno (Opcional)
Para mayor seguridad, considera usar variables de entorno:
```python
# En app.py, cambiar:
app.secret_key = os.environ.get('SECRET_KEY', 'tu-clave-secreta-aqui')
```

## Funcionalidades de la Aplicación

### Para Usuarios:
- ✅ **Registro y login** con validación
- ✅ **Picks semanales** con logos de equipos
- ✅ **Dashboard interactivo** con estado en tiempo real
- ✅ **Clasificación semanal** con porcentajes de acierto
- ✅ **Cuadrícula de picks** integrada para ver todos los picks
- ✅ **Historial de ganadores** por semana

### Para Administradores:
- ✅ **Panel de administración** completo
- ✅ **Gestión de semanas** y bloqueo de picks
- ✅ **Procesamiento de resultados** automático desde ESPN API
- ✅ **Vista de juegos en tiempo real** con STATUS_IN_PROGRESS
- ✅ **Gestión de usuarios** y estadísticas

### Características Técnicas:
- ✅ **ESPN NFL API** integrada con manejo de SSL
- ✅ **Timezone CDMX** para horarios locales
- ✅ **HTMX** para actualizaciones dinámicas
- ✅ **Tailwind CSS** para diseño responsive
- ✅ **SQLite** para base de datos ligera
- ✅ **Logos oficiales** de equipos NFL

## Post-Despliegue

### Configuración Inicial:
1. Acceder como admin con las credenciales arriba
2. Configurar la semana actual en el panel de administración
3. Verificar que los logos de equipos carguen correctamente
4. Invitar a usuarios a registrarse

### Mantenimiento Semanal:
1. Actualizar la semana en el panel de admin
2. Procesar resultados después de cada semana
3. Verificar que la clasificación se actualice correctamente

## Seguridad

### Recomendaciones Adicionales:
- Cambiar la `SECRET_KEY` por una clave única y segura
- Considerar cambiar la contraseña de admin después del primer login
- Hacer backups regulares de `quinielas.db`
- Monitorear el uso del API de ESPN para evitar rate limits

## Soporte
Para cualquier problema o pregunta sobre el despliegue, revisar:
- Logs en PythonAnywhere dashboard
- Verificar que todas las dependencias estén instaladas
- Confirmar que los paths en `wsgi.py` sean correctos