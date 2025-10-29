import os
from pathlib import Path
from contextlib import asynccontextmanager
from Functions import dataset_manager
from dotenv import load_dotenv
from dask.distributed import Client, LocalCluster

# ============== Root directory ================
load_dotenv()
BACKEND_DIR = Path(__file__).parent.parent       # backend/
PROJECT_ROOT = BACKEND_DIR.parent   # DigiH2O-Platform/
PROJECT_STATIC_ROOT = os.path.join(BACKEND_DIR, "Delft_Projects")
STATIC_DIR_BACKEND = os.path.join(BACKEND_DIR, "static")
STATIC_DIR_FRONTEND = os.path.join(PROJECT_ROOT, "frontend", "static")
DELFT_PATH = os.getenv("DELFT3D_PATH")
GRID_PATH = os.getenv('GRID_PATH')

# ============== Lifespan ================
@asynccontextmanager
async def lifespan(app):
    # PROJECT_DIR of current directory
    app.state.PROJECT_DIR = None
    # WAQ model type
    app.state.waq_model = None
    # Generate Dassh cluster
    cluster = LocalCluster(n_workers=2, threads_per_worker=2, memory_limit='4GB')
    client = Client(cluster)
    print(f"🚀 Dask cluster started with dashboard link: {cluster.dashboard_link}")
    app.state.dask_client = client
    # Dataset
    app.state.dataset_manager = dataset_manager.DatasetManager()
    yield
    # Close datasets and clear memory
    client.close()
    app.state.dataset_manager.close()
    print("🛑 Dask cluster closed")