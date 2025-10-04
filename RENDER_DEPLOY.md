# Render Deployment Configuration

## Configuración del Web Service

### Build Command:
```bash
pip install -r requirements.txt
```

### Start Command:  
```bash
python migrate.py && gunicorn app:app --bind 0.0.0.0:$PORT
```

### Environment Variables:
- `FLASK_ENV=production`
- `SECRET_KEY=your-super-secure-random-key-here`
- `DATABASE_URL=` (automáticamente configurado por Render PostgreSQL)

## Pasos para Deploy:

1. **Crear PostgreSQL Database en Render:**
   - Ir a Dashboard > New > PostgreSQL
   - Name: `quiniela-postgres`
   - Plan: Free
   - Copiar la DATABASE_URL

2. **Crear Web Service en Render:**
   - Ir a Dashboard > New > Web Service  
   - Connect tu repositorio de GitHub
   - Name: `quiniela-nfl`
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python migrate.py && gunicorn app:app --bind 0.0.0.0:$PORT`
   - Plan: Free

3. **Configurar Variables de Entorno:**
   - `FLASK_ENV=production`
   - `SECRET_KEY=` (genera una clave segura)
   - `DATABASE_URL=` (copia desde tu PostgreSQL service)

4. **Deploy:**
   - Render automáticamente hará deploy cuando hagas push a main
   - La migración se ejecutará automáticamente

## URLs:
- **PostgreSQL:** `quiniela-postgres-xxxx.render.com`  
- **Web App:** `quiniela-nfl-xxxx.onrender.com`

## Notas:
- La primera migración puede tomar algunos minutos
- Los logs están disponibles en el dashboard de Render
- Las variables de entorno deben configurarse ANTES del primer deploy