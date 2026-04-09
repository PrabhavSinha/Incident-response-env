# Re-export from root app.py for multi-mode deployment compatibility
from app import app, main

__all__ = ["app", "main"]
