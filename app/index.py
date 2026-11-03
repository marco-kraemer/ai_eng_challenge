"""Vercel's supported FastAPI entrypoint; local/Docker entrypoint remains app.web."""
from app.web import app

__all__ = ['app']
