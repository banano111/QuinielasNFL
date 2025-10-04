#!/usr/bin/env bash
# Build script simplificado para Render

echo "� Actualizando pip..."
pip install --upgrade pip

echo "� Instalando dependencias..."
pip install -r requirements.txt

echo "🗄️ Ejecutando migraciones..."
python migrate.py

echo "✅ Build completado!"