import os
from pathlib import Path
from contextlib import asynccontextmanager

# ============== Root directory ================
ROOT_DIR = Path(__file__).parent
PROJECT_STATIC_ROOT = os.path.join(ROOT_DIR, "Delft_Projects")

# ============== Lifespan ================
@asynccontextmanager
async def lifespan(app):
    # PROJECT_DIR of current directory
    app.state.PROJECT_DIR = None
    # Template, static
    app.state.templates = None
    app.state.config = None
    # NetCDF
    app.state.hyd_his = None
    app.state.hyd_map = None
    app.state.waq_his = None
    app.state.waq_map = None
    app.state.grid = None
    app.state.n_layers = None
    app.state.layer_reverse = None
    yield
    check = False
    # Close datasets and clear memory
    for dataset in [app.state.hyd_his, app.state.hyd_map,
                    app.state.waq_his, app.state.waq_map]:
        if dataset: 
            check = True
            dataset.close()
    if check: print("🛑 NetCDF files closed at shutdown")