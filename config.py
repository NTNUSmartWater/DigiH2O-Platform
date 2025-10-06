import os
from pathlib import Path
from contextlib import asynccontextmanager
from Functions import dataset_manager
from dotenv import load_dotenv

# ============== Root directory ================
load_dotenv()
ROOT_DIR = Path(__file__).parent
PROJECT_STATIC_ROOT = os.path.join(ROOT_DIR, "Delft_Projects")
DELFT_PATH = os.getenv("DELFT3D_PATH")

# ============== Lifespan ================
@asynccontextmanager
async def lifespan(app):
    # PROJECT_DIR of current directory
    app.state.PROJECT_DIR = None
    # WAQ model type
    app.state.waq_model = None
    # Dataset
    app.state.dataset_manager = dataset_manager.DatasetManager()
    yield
    # Close datasets and clear memory
    app.state.dataset_manager.close()