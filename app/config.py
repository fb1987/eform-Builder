# app/config.py
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.1")  # adjust as needed
# Allowed origins for Webflow or your domains (comma-separated)
ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", 
    "https://*.webflow.io, https://webflow.com"
).split(",") if o.strip()]

# Optional: set to "1" to include more verbose logs
DEBUG = os.getenv("DEBUG", "0") == "1"

# Filenames & defaults
DEFAULT_NOTE_VERSION = int(os.getenv("DEFAULT_NOTE_VERSION", "2"))
SERVICE_NAME = os.getenv("SERVICE_NAME", "eform-builder")
