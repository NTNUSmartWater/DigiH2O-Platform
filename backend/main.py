import uvicorn, os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware

# Import internally backend modules
from config import STATIC_DIR_BACKEND, STATIC_DIR_FRONTEND, PROJECT_STATIC_ROOT, lifespan
from Functions import route_page, process_manager, wq_process, project_manager, run_simulation

app = FastAPI(lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount common static files for Mobirise (frontend)
app.mount("/assets/images", StaticFiles(directory=os.path.join(STATIC_DIR_FRONTEND, "assets/images")), name="mobirise_images")
app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR_FRONTEND, "assets")), name="assets")
# My images
app.mount("/images", StaticFiles(directory=os.path.join(STATIC_DIR_BACKEND, "images")), name="my_images")
app.mount("/static", StaticFiles(directory=os.path.join(STATIC_DIR_BACKEND, "static")), name="static")
app.mount("/projects_static", StaticFiles(directory=PROJECT_STATIC_ROOT), name="projects_static")

# Mount routes
app.include_router(route_page.router)
app.include_router(process_manager.router)
app.include_router(project_manager.router)
app.include_router(run_simulation.router)
app.include_router(wq_process.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload_dirs=['.'], reload=True) # Remove reload=True for production