#!/usr/bin/python3.10

"""
WSGI config for QuinielasApp on PythonAnywhere.

Para más información sobre esta configuración, visita:
https://help.pythonanywhere.com/pages/Flask/
"""

import sys
import os

# Agregar el directorio de tu aplicación al Python path
path = '/home/banano111/QuinielasApp'  # Cambiar 'tuusuario' por tu username de PythonAnywhere
if path not in sys.path:
    sys.path.insert(0, path)

# Importar tu aplicación Flask
from app import app as application

if __name__ == "__main__":
    application.run()