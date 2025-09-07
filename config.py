import os
from pathlib import Path
from contextlib import asynccontextmanager

# ============== Root directory ================
ROOT_DIR = Path(__file__).parent
PROJECT_STATIC_ROOT = os.path.join(ROOT_DIR, "Delft_Projects")

# ============== Lifespan ================
@asynccontextmanager
async def lifespan(app):
    # BASE_DIR of current directory
    app.state.BASE_DIR = None
    # Template, static
    app.state.templates = None
    app.state.project_selected = None
    # NetCDF
    app.state.data_his = None
    app.state.data_map = None
    app.state.data_wq_his = None
    app.state.data_wq_map = None
    app.state.grid = None
    app.state.n_layers = None
    app.state.layer_reverse = None
    yield
    check = False
    # Close datasets and clear memory
    for dataset in [app.state.data_his, app.state.data_map, 
                    app.state.data_wq_his, app.state.data_wq_map]:
        if dataset: 
            check = True
            dataset.close()
    if check: print("🛑 NetCDF files closed at shutdown")