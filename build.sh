#!/usr/bin/env bash
# Build script para Render

# Instalar dependencias de Python
pip install -r requirements.txt

# Crear el directorio para la base de datos si no existe
mkdir -p data

# La aplicación se iniciará automáticamente con el start command