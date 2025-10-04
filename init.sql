-- Script de inicialización para PostgreSQL
-- Este archivo se ejecuta automáticamente al crear el contenedor

-- Crear extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Asegurar que la base de datos existe
-- (Ya se crea automáticamente por POSTGRES_DB)

-- Configuraciones adicionales si las necesitas
-- ALTER DATABASE quiniela_dev SET timezone TO 'UTC';