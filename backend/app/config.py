import os
from pathlib import Path
from contextlib import asynccontextmanager
from Functions import dataset_manager
from dotenv import load_dotenv

# ============== Root directory ================
load_dotenv()
BACKEND_DIR = Path(__file__).parent.parent       # backend/
PROJECT_STATIC_ROOT = os.getenv(
    "PROJECT_STATIC_ROOT", os.path.join(BACKEND_DIR, "Delft_Projects")
)
STATIC_DIR_BACKEND = os.getenv(
    "STATIC_DIR_BACKEND", os.path.join(BACKEND_DIR, "static")
)
STATIC_DIR_FRONTEND = os.getenv(
    "STATIC_DIR_FRONTEND", os.path.join(BACKEND_DIR.parent, "frontend", "static")
)
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