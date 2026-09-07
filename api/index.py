"""Vercel entrypoint for the AERIS FastAPI application."""

from aeris.api.main import app

__all__ = ["app"]