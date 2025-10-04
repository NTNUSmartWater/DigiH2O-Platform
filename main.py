import uvicorn, config
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from Functions import route_page, process_manager, wq_process
from Functions import project_manager, run_simulation
from config import PROJECT_STATIC_ROOT

app = FastAPI(lifespan=config.lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount common static files for Mobirise
app.mount("/assets/images", StaticFiles(directory="static/assets/images"), name="mobirise_images")
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")
# My images
app.mount("/images", StaticFiles(directory="static/images"), name="my_images")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/projects_static", StaticFiles(directory=PROJECT_STATIC_ROOT), name="projects_static")

# Mount routes
app.include_router(route_page.router)
app.include_router(process_manager.router)
app.include_router(project_manager.router)
app.include_router(run_simulation.router)
app.include_router(wq_process.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload_dirs=['.'], reload=True) # Remove reload=True for production