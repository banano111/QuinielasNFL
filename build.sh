#!/usr/bin/env bash
# Build script para Render

echo "🔨 Instalando dependencias de Python..."
pip install -r requirements.txt

echo "🗄️ Configurando base de datos..."
# Ejecutar migraciones para crear tablas en PostgreSQL
python migrate.py

echo "✅ Build completado exitosamente!"