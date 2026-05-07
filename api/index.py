"""
Vercel Python serverless entry point for AssetBase backend.
"""
import sys
import os

# Add backend/ to path so all modules resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app  # noqa: F401 — Vercel picks up 'app' as the WSGI handler
