import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from config import ROOT_DIR

router = APIRouter()
templates = Jinja2Templates(directory="static/templates")

# Select Project
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    folder = Jinja2Templates(directory=ROOT_DIR)
    return folder.TemplateResponse("index.html", {"request": request})

# Select platform
@router.get("/visualization")
def visualization(request: Request):
    template_file = "delft3D.html"
    template_path = os.path.join(ROOT_DIR, "static", "templates", template_file)
    if not os.path.exists(template_path): 
        return templates.TemplateResponse("error.html",
            {"request": request, "message": "File not found."})
    return templates.TemplateResponse(template_file, {"request": request})

# Load contact page
@router.get("/load_contact")
def load_contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

# Load open project
@router.get("/open_project")
def open_project(request: Request):
    return templates.TemplateResponse("projectSelector.html", {"request": request})

# Load new hyd project
@router.get("/new_HYD_project")
def new_HYD_project(request: Request):
    return templates.TemplateResponse("projectHYDCreator.html", {"request": request})

# Load new wq project
@router.get("/new_WQ_project")
def new_WQ_project(request: Request):
    return templates.TemplateResponse("projectWQCreator.html", {"request": request})

# Run grid generator
@router.get("/grid_generation")
def grid_generation(request: Request):
    return templates.TemplateResponse("gridGenerator.html", {"request": request})

# Run simulation page
@router.get("/run_hyd_simulation")
def run_hyd_simulation(request: Request):
    return templates.TemplateResponse("simulationHYDRunner.html", {"request": request})

# Load favicon
@router.get("/favicon.ico")
def favicon():
    return FileResponse("static/images/Logo.png")
