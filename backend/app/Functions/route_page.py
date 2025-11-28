import os, json
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from app.config import STATIC_DIR_FRONTEND, STATIC_DIR_BACKEND
from Functions import functions
from redis.asyncio.lock import Lock

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(STATIC_DIR_FRONTEND, "templates"))

# ==================== Helper ====================
async def get_project_data(request: Request, project_name: str):
    # Get project data from Redis, if not found return None
    key = f"project:{project_name}"
    data = await request.app.state.redis.get(key)
    if data: return json.loads(data)
    return None
async def set_project_data(request: Request, project_name: str, data: dict):
    key = f"project:{project_name}"
    await request.app.state.redis.set(key, json.dumps(data))

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
    template_path = os.path.join(STATIC_DIR_FRONTEND, "templates", template_file)
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
async def load_popupMenu(request: Request, htmlFile: str, project_name: str = None):
    # Show project menu, read config from Redis
    if htmlFile == 'projectMenu.html':
        return templates.TemplateResponse(htmlFile, {"request": request})
    if not project_name:
        return HTMLResponse("<p>No project selected</p>", status_code=400)
    project_data = await get_project_data(request, project_name)
    if not project_data:
        return HTMLResponse(f"<p>Project '{project_name}' not found</p>", status_code=404)
    path = os.path.join(STATIC_DIR_FRONTEND, "templates", htmlFile)
    if not os.path.exists(path):
        return HTMLResponse(f"<p>Popup menu template not found</p>", status_code=404)
    # Get config from Redis, if not found scan files to get variables
    if "config" not in project_data:
        files = [
            project_data.get("hyd_his"), project_data.get("hyd_map"),
            project_data.get("waq_his"), project_data.get("waq_map")
        ]
        waq_model = project_data.get("waq_model")
        project_data["config"] = await functions.getVariablesNames(files, waq_model)
        # Acquire Redis lock to prevent race condition
        redis = request.app.state.redis
        lock = Lock(redis, f"lock:project:{project_name}", timeout=10)  # 10s lock
        async with lock:
        # Save updated project data back to Redis
            await set_project_data(request, project_name, project_data)
    return templates.TemplateResponse(htmlFile, {"request": request, 'configuration': project_data["config"]})

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
    return templates.TemplateResponse("simulationHYDRunner.html", {"request": request})

# Load new wq project
@router.get("/new_WQ_project")
def new_WQ_project(request: Request):
    return templates.TemplateResponse("projectWQCreator.html", {"request": request})

# Run grid generator
@router.get("/grid_generation")
def grid_generation(request: Request):
    return templates.TemplateResponse("gridGenerator.html", {"request": request})

# Load favicon
@router.get("/favicon.ico")
def favicon():
    return FileResponse(os.path.join(STATIC_DIR_BACKEND, "images", "Logo.png"))
