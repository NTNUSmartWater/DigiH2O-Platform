import os, traceback, json, shutil, subprocess, io, mercantile, rasterio
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, Response
from fastapi.responses import JSONResponse
from Functions import functions, flowFunctions
from config import PROJECT_STATIC_ROOT
import numpy as np
from PIL import Image
from rasterio.shutil import copy as rio_copy
from rasterio.enums import Resampling



router = APIRouter()





@router.get("/terrain_tiles/{project}/{filename}/{z}/{x}/{y}.png")
def terrain_tiles(project: str, filename: str, z: int, x: int, y: int):
    tif_path = os.path.join(PROJECT_STATIC_ROOT, project, "terrains", filename)
    meta_path = tif_path.replace(".tif", ".json")
    if not os.path.exists(tif_path) or not os.path.exists(meta_path):
        return Response(status_code=404)
    # ---- Load global min/max ----
    with open(meta_path, "r") as f:
        meta = json.load(f)
    global_min, global_max = meta["min"], meta["max"]
    with rasterio.open(tif_path) as src:
        bounds = mercantile.bounds(x, y, z)
        window = rasterio.windows.from_bounds(
            bounds.west, bounds.south, bounds.east, bounds.north, src.transform
        )
        data = src.read(1, window=window, out_shape=(256, 256), resampling=Resampling.bilinear)
        # Normalize data
        data = np.nan_to_num(data)
        if global_max > global_min:
            data = (255*(data - global_min) / (global_max - global_min))
            data = np.clip(data, 0, 255).astype(np.uint8)
        else: data = np.zeros((256, 256), dtype=np.uint8)
        img = Image.fromarray(data)
        buf = io.BytesIO()
        img.save(buf, format='png')
    return Response(content=buf.getvalue(), media_type="image/png")

@router.post("/terrain_upload")
async def terrain_upload(file: UploadFile = File(...), projectName: str = Form(...),
                         user=Depends(functions.basic_auth)):
    try:
        project_name, _ = functions.project_definer(projectName, user)
        save_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains")
        print(f"save_dir: {save_dir}")
        if not os.path.exists(save_dir): os.makedirs(save_dir)
        terrain_path = os.path.join(save_dir, file.filename)
        print(f"Uploading terrain: {terrain_path}")
        with open(terrain_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # Convert to COG
        cog_path = os.path.splitext(terrain_path)[0] + "_cog.tif"
        if not os.path.exists(cog_path):
            rio_copy(terrain_path, cog_path, driver='COG', compress='LZW')
        # Get min and max
        with rasterio.open(cog_path) as src:
            data = src.read(1, masked=True)
            global_min, global_max = float(data.min()), float(data.max())
        # Save metadata
        meta_path = cog_path.replace(".tif", ".json")
        with open(meta_path, 'w') as f:
            json.dump({'min': global_min, 'max': global_max}, f)
        tile_url = f"/terrain_tiles/{project_name}/{os.path.basename(cog_path)}/{{z}}/{{x}}/{{y}}.png"
        return JSONResponse({'status': 'ok', 'content': {'tile_url': tile_url, 'min': global_min, 'max': global_max}})
    except Exception as e:
        print('/terrain_upload:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

