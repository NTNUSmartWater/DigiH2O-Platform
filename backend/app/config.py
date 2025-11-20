import os
from pathlib import Path
from contextlib import asynccontextmanager
from Functions import dataset_manager
from dotenv import load_dotenv

# ============== Root directory ================
load_dotenv()
BACKEND_DIR = Path(__file__).parent.parent       # backend/
env_mode = os.getenv("ENV", "development")
if env_mode == "development":
    PROJECT_STATIC_ROOT = os.getenv("PROJECT_STATIC_ROOT")
    STATIC_DIR_BACKEND = os.getenv("STATIC_DIR_BACKEND")
    STATIC_DIR_FRONTEND = os.getenv("STATIC_DIR_FRONTEND")
else:
    PROJECT_STATIC_ROOT = "/app/Delft_Projects"
    STATIC_DIR_BACKEND = "/app/static"
    STATIC_DIR_FRONTEND = "/usr/share/nginx/html/static"
DELFT_PATH = os.getenv("DELFT3D_PATH")
GRID_PATH = os.getenv('GRID_PATH')

# ============== Lifespan ================
@asynccontextmanager
async def lifespan(app):
    # Dataset
    app.state.dataset_manager = dataset_manager.DatasetManager()
    yield
    try:
        app.state.dataset_manager.close()
    except Exception as e:
        print(f"⚠️ Dataset manager close error: {e}")