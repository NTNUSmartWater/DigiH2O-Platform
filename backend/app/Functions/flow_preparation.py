import os, traceback, json, shutil, io, mercantile, rasterio
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, Response
from fastapi.responses import JSONResponse
from Functions import functions, flowFunctions
from config import PROJECT_STATIC_ROOT
import numpy as np
from PIL import Image
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
import matplotlib.cm as cm



router = APIRouter()





@router.get("/{project}/terrain/{folder}/{filename}/{z}/{x}/{y}.png")
def terrain_tiles(project: str, folder: str, filename: str, z: int, x: int, y: int):
    try:
        tif_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project, "terrains", folder))
        tif_path = os.path.normpath(os.path.join(tif_folder, filename))
        # Get min and max
        with open(os.path.normpath(os.path.join(tif_folder, f"{folder}.json"))) as f:
            meta = json.load(f)
        global_min, global_max = float(meta.get("min", 0)), float(meta.get("max", 0))
        bounds = mercantile.xy_bounds(x, y, z)
        dst_transform = rasterio.transform.from_bounds(
            bounds.left, bounds.bottom, bounds.right, bounds.top, 256, 256
        )
        dst = np.full((256, 256), np.nan, dtype=np.float32)
        with rasterio.open(tif_path) as src:
            reproject( source=rasterio.band(src, 1), destination=dst,
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=dst_transform, dst_crs="EPSG:3857",
                resampling=Resampling.bilinear, dst_nodata=np.nan
            )
            valid_mask = ~np.isnan(dst)
            norm = np.zeros_like(dst)
            norm[valid_mask] = (dst[valid_mask] - global_min) / (global_max - global_min)
            norm = np.clip(norm, 0, 1)
            rgba_map = cm.get_cmap("terrain")(norm)
            rgb = (rgba_map[:, :, :3] * 255).astype(np.uint8)
            alpha = (valid_mask * 255).astype(np.uint8)
            rgba = np.dstack([rgb, alpha])
            img, buf = Image.fromarray(rgba, mode="RGBA"), io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/terrain_upload")
async def terrain_upload(file: UploadFile = File(...), projectName: str = Form(...),
                         user=Depends(functions.basic_auth)):
    try:
        project_name, _ = functions.project_definer(projectName, user)
        dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains"))
        os.makedirs(dir, exist_ok=True)
        name, dst_crs = file.filename.rstrip(".tif"), "EPSG:3857"
        save_dir = os.path.normpath(os.path.join(dir, name))
        if os.path.exists(save_dir): shutil.rmtree(save_dir)
        os.makedirs(save_dir, exist_ok=True)
        terrain_path = os.path.normpath(os.path.join(save_dir, file.filename))
        with open(terrain_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # Convert to COG
        cog_path = os.path.splitext(terrain_path)[0] + "_cog.tif"
        with rasterio.open(terrain_path) as src:
            transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
            profile = src.profile.copy()
            profile.update({"crs": dst_crs, "transform": transform, "width": width,
                "height": height, "driver": "COG", "compress": "LZW", "tiled": True
            })
            with rasterio.open(cog_path, "w", **profile) as dst:
                reproject(
                    source=rasterio.band(src, 1), destination=rasterio.band(dst, 1),
                    src_transform=src.transform, src_crs=src.crs,
                    dst_transform=transform, dst_crs=dst_crs,
                    resampling=Resampling.bilinear
                )
        # Get min and max
        with rasterio.open(cog_path) as src:
            data = src.read(1, masked=True)
            global_min, global_max = float(data.min()), float(data.max())
        meta_path = os.path.splitext(terrain_path)[0] + ".json"
        with open(meta_path, "w") as f:
            json.dump({"min": global_min, "max": global_max}, f)
        tile_url = f"/{project_name}/terrain/{name}/{os.path.basename(cog_path)}/{{z}}/{{x}}/{{y}}.png"
        contents = {"tile_url": tile_url, "min": global_min, "max": global_max}
        return JSONResponse({'status': 'ok', 'content': contents})
    except Exception as e:
        print('/terrain_upload:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/fill_terrain")
async def fill_terrain(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        file_name = body.get('filename')
        folder = file_name.rstrip(".tif")
        fill_name, json_file = folder + "_filled.tif", f"{folder}.json"
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains", folder))
        os.makedirs(dir, exist_ok=True)
        dtm_path = os.path.normpath(os.path.join(dir, file_name))
        fill_path = os.path.normpath(os.path.join(dir, fill_name))
        if os.path.exists(fill_path): functions.safe_remove(fill_path)
        flowFunctions.fill_sink(dtm_path, fill_path)
        with rasterio.open(fill_path) as src:
            data = src.read(1, masked=True)
            global_min, global_max = float(data.min()), float(data.max())
        meta_path = os.path.normpath(os.path.join(dir, json_file))
        with open(meta_path, "w") as f:
            json.dump({"min": global_min, "max": global_max}, f)
        tile_url = f"/{project_name}/terrain/{folder}/{fill_name}/{{z}}/{{x}}/{{y}}.png"
        contents = {"tile_url": tile_url, "min": global_min, "max": global_max}
        return JSONResponse({'status': 'ok', 'content': contents, 'message': "Fill terrain successfully."})
    except Exception as e:
        print('/fill_terrain:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/fill_check")
async def fill_check(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    file_name = body.get('filename')
    folder = file_name.rstrip(".tif")
    project_name, _ = functions.project_definer(body.get('projectName'), user)
    dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains", folder))
    status, message = "error", "No fill terrain found. Please upload and fill terrain first."
    fill_path = os.path.normpath(os.path.join(dir, folder + "_filled.tif"))
    if os.path.exists(fill_path): status = "ok"
    return JSONResponse({'status': status, 'message': message})

@router.post("/flow_direction")
async def flow_direction(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        file_name = body.get('filename')
        folder = file_name.rstrip(".tif")
        flow_name, json_file = folder + "_flow.tif", f"{folder}.json"
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains", folder))
        fill_path = os.path.normpath(os.path.join(dir, folder + "_filled.tif"))
        flow_path = os.path.normpath(os.path.join(dir, flow_name))
        if os.path.exists(flow_path): functions.safe_remove(flow_path)
        flowFunctions.flow_direction(fill_path, flow_path)
        with rasterio.open(flow_path) as src:
            data = src.read(1, masked=True)
            global_min, global_max = float(data.min()), float(data.max())
        meta_path = os.path.normpath(os.path.join(dir, json_file))
        with open(meta_path, "w") as f:
            json.dump({"min": global_min, "max": global_max}, f)
        tile_url = f"/{project_name}/terrain/{folder}/{flow_name}/{{z}}/{{x}}/{{y}}.png"
        contents = {"tile_url": tile_url, "min": global_min, "max": global_max}
        return JSONResponse({'status': 'ok', 'content': contents, 'message': "Flow direction successfully."})
    except Exception as e:
        print('/flow_direction:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})




