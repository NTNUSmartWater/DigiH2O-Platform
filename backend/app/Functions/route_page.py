import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.config import STATIC_DIR_FRONTEND, STATIC_DIR_BACKEND
from Functions import functions

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(STATIC_DIR_FRONTEND, "templates"))

# Select Project
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
async def load_popupMenu(request: Request, htmlFile: str):
    if htmlFile == 'projectMenu.html':
        return templates.TemplateResponse(htmlFile, {"request": request})
    if not request.app.state.templates:
        return HTMLResponse("<p>No project selected</p>", status_code=400)
    path = os.path.join(STATIC_DIR_FRONTEND, "templates", htmlFile)
    if not os.path.exists(path):
        return HTMLResponse(f"<p>Popup menu template not found</p>", status_code=404)
    if not request.app.state.config:
        if (request.app.state.waq_his or request.app.state.waq_map) and not request.app.state.waq_model:
            return JSONResponse({"status": 'error', "message": "Some WAQ-related parameters are missing.\nConsider running the model again."})
        files = [request.app.state.hyd_his, request.app.state.hyd_map, 
            request.app.state.waq_his, request.app.state.waq_map]
        request.app.state.config = functions.getVariablesNames(files, request.app.state.waq_model)
    return templates.TemplateResponse(htmlFile, {"request": request, 'configuration': request.app.state.config})

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
