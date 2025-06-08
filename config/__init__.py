"""
Ax-Shell configuration package.
"""
# Import only specific names actually defined in data.py
# This prevents circular imports by not importing everything
from .data import APP_NAME, APP_NAME_CAP, CACHE_DIR, CONFIG_FILE
