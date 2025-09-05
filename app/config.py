# app/config.py
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0"))  # let you set 1.0 from env

# CORS
# Exact origins (comma-separated). NOTE: wildcards like https://*.webflow.io do NOT work here.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
# Regex alternative for subdomains, e.g., r"^https://([a-z0-9-]+)\.webflow\.io$"
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX", "")
# MVP override: allow all origins (no credentials). Safe since we do not use cookies.
ALLOW_ALL_ORIGINS = os.getenv("ALLOW_ALL_ORIGINS", "0") == "1"
# Expose headers so your JS can read them (e.g., Content-Disposition for filename)
EXPOSE_HEADERS = [h.strip() for h in os.getenv(
    "EXPOSE_HEADERS", "Content-Disposition,X-Service"
).split(",") if h.strip()]

DEBUG = os.getenv("DEBUG", "0") == "1"
DEFAULT_NOTE_VERSION = int(os.getenv("DEFAULT_NOTE_VERSION", "2"))
SERVICE_NAME = os.getenv("SERVICE_NAME", "eform-builder")
