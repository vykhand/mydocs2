import os

from dotenv import load_dotenv

load_dotenv()

SERVICE_NAME = os.environ.get("SERVICE_NAME", "mydocs")

ROOT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FOLDER = os.environ.get("MYDOCS_DATA_FOLDER", os.path.join(ROOT_FOLDER, "data"))
CONFIG_ROOT = os.environ.get("MYDOCS_CONFIG_ROOT", os.path.join(ROOT_FOLDER, "config"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

MONGO_URL = os.environ.get("MONGO_URL")
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")

AZURE_DI_ENDPOINT = os.environ.get("AZURE_DI_ENDPOINT")
AZURE_DI_API_KEY = os.environ.get("AZURE_DI_API_KEY")
AZURE_DI_API_VERSION = "2024-11-30"

AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_BASE = os.environ.get("AZURE_OPENAI_API_BASE")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Azure Blob Storage (managed backend)
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_ACCOUNT_NAME = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_STORAGE_CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "managed")

# Storage backend selection
STORAGE_BACKEND = os.environ.get("MYDOCS_STORAGE_BACKEND", "local")
