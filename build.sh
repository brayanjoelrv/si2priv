#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# FORZAR: Limpiar el registro de la migración 0008 de la BD por si Render la bloqueó antes
python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute(\"DELETE FROM django_migrations WHERE app='P2_Gestion_Clinica' AND name LIKE '0008%'\")" || true

# Falso-aplicar migraciones conflictivas si ya existen en la BD
python safe_migrate.py

# Generar y comprimir recursos estáticos a través de WhiteNoise
python manage.py collectstatic --no-input
