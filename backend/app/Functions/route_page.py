import os, msgpack
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from app.config import STATIC_DIR_FRONTEND, STATIC_DIR_BACKEND
from Functions import functions

router = APIRouter()
templates = Jinja2Templates(directory=os.path.normpath(os.path.join(STATIC_DIR_FRONTEND, "templates")))

# ==================== Routes ====================
# Home page
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    folder = Jinja2Templates(directory=os.path.dirname(STATIC_DIR_FRONTEND))
    return folder.TemplateResponse("index.html", {"request": request})

# Select platform
@router.get("/visualization")
def visualization(request: Request):
    template_file = "delft3D.html"
    template_path = os.path.normpath(os.path.join(STATIC_DIR_FRONTEND, "templates", template_file))
    if not os.path.exists(template_path): 
        return templates.TemplateResponse("error.html",
            {"request": request, "message": "File not found."})
    return templates.TemplateResponse(template_file, {"request": request})

# Load contact page
@router.get("/load_contact")
def load_contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

# Load popup menu
@router.get("/load_popupMenu", response_class=HTMLResponse)
async def load_popupMenu(request: Request, htmlFile: str, project_name: str = None, user=Depends(functions.basic_auth)):
    # Show project menu, read config from Redis
    if htmlFile == 'projectMenu.html':
        return templates.TemplateResponse(htmlFile, {"request": request})
    if not project_name:
        return HTMLResponse(f"<p>Project '{project_name}' not found</p>", status_code=404)
    # Acquire Redis lock to prevent race condition
    redis = request.app.state.redis
    project_name, project_id = functions.project_definer(project_name, user)
    path = os.path.normpath(os.path.join(STATIC_DIR_FRONTEND, "templates", htmlFile))
    if not os.path.exists(path):
        return HTMLResponse(f"<p>Popup menu template not found</p>", status_code=404)
    # Get config from Redis, if not found scan files to get variables
    config_raw = await redis.hget(project_name, "config")
    # If config already exists → no race → render
    if config_raw:
        config = msgpack.unpackb(config_raw, raw=False)
        return templates.TemplateResponse(htmlFile, {"request": request, 'configuration': config})
    lock = redis.lock(f"{project_id}:init_config", timeout=10)  # 10s lock
    async with lock:
        # Double check: Is there anyone else running?
        config_raw = await redis.hget(project_name, "config")
        if config_raw:
            config = msgpack.unpackb(config_raw, raw=False)
            return templates.TemplateResponse(htmlFile, {"request": request, 'configuration': config})
        # Create config the first time
        project_cache = request.app.state.project_cache.setdefault(project_name)
        files = [project_cache.get("hyd_his"), project_cache.get("hyd_map"),
                project_cache.get("waq_his"), project_cache.get("waq_map")]
        waq_model_raw = await redis.hget(project_name, "waq_model")
        waq_model = waq_model_raw.decode() if waq_model_raw else "unknown"
        config_obj = functions.getVariablesNames(files, waq_model)
        # Restructure configuration
        config = {**config_obj.get("hyd", {}), **config_obj.get("waq", {})}
        for k, v in config_obj.items():
            if k not in ("hyd", "waq", "meta"):
                config[k] = v
        # Save updated project data back to Redis
            await redis.hset(project_name, "config", msgpack.packb(config, use_bin_type=True))
    return templates.TemplateResponse(htmlFile, {"request": request, 'configuration': config})

# Load open project
@router.get("/open_project")
def open_project(request: Request):
    return templates.TemplateResponse("projectSelector.html", {"request": request})

# Load new hyd project
@router.get("/new_HYD_project")
def new_HYD_project(request: Request):
    return templates.TemplateResponse("projectHYDCreator.html", {"request": request})

# Run simulation page
@router.get("/run_hyd_simulation")
def run_hyd_simulation(request: Request):
    return templates.TemplateResponse("simulationRunner.html", {"request": request, "mode": "hyd"})

# Load new wq project
@router.get("/new_WQ_project")
def new_WQ_project(request: Request):
    return templates.TemplateResponse("projectWQCreator.html", {"request": request})

# Load new wq project
@router.get("/run_WQ_project")
def run_WQ_project(request: Request):
    return templates.TemplateResponse("simulationRunner.html", {"request": request, "mode": "waq"})

# Run grid generator
@router.get("/grid_generation")
def grid_generation(request: Request):
    return templates.TemplateResponse("gridGenerator.html", {"request": request})

# Load favicon
@router.get("/favicon.ico")
def favicon():
    return FileResponse(os.path.normpath(os.path.join(STATIC_DIR_BACKEND, "images", "Logo.png")))
