import os
from pathlib import Path
from contextlib import asynccontextmanager
from Functions import dataset_manager
from dotenv import load_dotenv
# from dask.distributed import Client, LocalCluster

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
    # # Generate Dassh cluster
    # cluster = client = None
    # try:
    #     cluster = LocalCluster(n_workers=2, threads_per_worker=2, 
    #         memory_limit='4GB', dashboard_address=":8787", silence_logs=False)
    #     client = Client(cluster)
    #     print(f"🚀 Dask cluster started with dashboard link: {cluster.dashboard_link}")
    #     app.state.dask_client = client
    # except Exception as e: 
    #     print(f"⚠️ Failed to start Dask cluster: {e}")
    #     app.state.dask_client = None
    # Dataset
    app.state.dataset_manager = dataset_manager.DatasetManager()
    yield
    app.state.dataset_manager.close()

    # try:
    #     yield
    # finally:
    #     try:
    #         if client:
    #             client.close(timeout=5)
    #         if cluster:
    #             cluster.close(timeout=5)
    #         print("🛑 Dask cluster closed cleanly")
    #     except Exception as e:
    #         print(f"⚠️ Dask cluster shutdown error: {e}")
    # # Close datasets and clear memory
    # try:
    #     app.state.dataset_manager.close()
    # except Exception as e:
    #     print(f"⚠️ Dataset manager close error: {e}")