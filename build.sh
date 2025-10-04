#!/usr/bin/env bash
# Build script para Render

echo "🔨 Instalando dependencias del sistema..."
# Instalar librerías necesarias para PostgreSQL
apt-get update && apt-get install -y libpq-dev gcc

echo "🔨 Instalando dependencias de Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🗄️ Configurando base de datos..."
# Ejecutar migraciones para crear tablas en PostgreSQL
python migrate.py

echo "✅ Build completado exitosamente!"