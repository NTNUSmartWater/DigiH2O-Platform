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





@router.get("/{project}/terrains/{filename}/{z}/{x}/{y}.png")
def terrain_tiles(project: str, filename: str, z: int, x: int, y: int):
    try:
        tif_path = os.path.join(PROJECT_STATIC_ROOT, project, "terrains", filename)
        tif_path = os.path.normpath(tif_path)
        # Get min and max
        with open(tif_path.replace(".tif", ".json")) as f:
            meta = json.load(f)
        global_min, global_max = float(meta.get("min", 0)), float(meta.get("max", 0))
        # EPSG:3857 tile bounds
        bounds = mercantile.xy_bounds(x, y, z)
        dst_transform = rasterio.transform.from_bounds(
            bounds.left, bounds.bottom, bounds.right, bounds.top, 256, 256
        )
        dst = np.full((256, 256), np.nan, dtype=np.float32)
        with rasterio.open(tif_path) as src:
            reproject(
                source=rasterio.band(src, 1),
                destination=dst,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs="EPSG:3857",
                resampling=Resampling.bilinear,
                dst_nodata=np.nan
            )
            valid_mask = ~np.isnan(dst)
            norm = np.zeros_like(dst)
            norm[valid_mask] = (dst[valid_mask] - global_min) / (global_max - global_min)
            norm = np.clip(norm, 0, 1)
            
            # norm_for_colormap = norm.copy()
            # norm_for_colormap[~valid_mask] = 0
            rgba_map = cm.get_cmap("terrain")(norm)
            rgb = (rgba_map[:, :, :3] * 255).astype(np.uint8)
            alpha = (valid_mask * 255).astype(np.uint8)
            rgba = np.dstack([rgb, alpha])


            # window = rasterio.windows.from_bounds(
            #     bounds.left, bounds.bottom, bounds.right, bounds.top, src.transform
            # ).round_offsets().round_lengths()
            # data = src.read(1, window=window, out_shape=(256, 256), boundless=True, masked=True)
            # valid_mask = np.logical_not(data.mask)
            # norm = np.zeros_like(data, dtype=float)
            # norm[valid_mask] = (data.data[valid_mask] - global_min) / (global_max - global_min)
            # norm = np.clip(norm, 0, 1)
            # # Colormap terrain
            # rgb = (cm.get_cmap("terrain")(norm)[:, :, :3] * 255).astype(np.uint8)
            # alpha = (valid_mask * 255).astype(np.uint8)
            # rgba = np.dstack([rgb, alpha])
            img, buf = Image.fromarray(rgba, mode="RGBA"), io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            print("NaN count:", np.isnan(norm).sum())
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/terrain_upload")
async def terrain_upload(file: UploadFile = File(...), projectName: str = Form(...),
                         user=Depends(functions.basic_auth)):
    try:
        project_name, _ = functions.project_definer(projectName, user)
        save_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains")
        save_dir, dst_crs = os.path.normpath(save_dir), "EPSG:3857"
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
        meta_path = os.path.splitext(cog_path)[0] + ".json"
        with open(meta_path, "w") as f:
            json.dump({"min": global_min, "max": global_max}, f)
        tile_url = f"/{project_name}/terrains/{os.path.basename(cog_path)}/{{z}}/{{x}}/{{y}}.png"
        return JSONResponse({'status': 'ok', 'content': {'tile_url': tile_url, 'min': global_min, 'max': global_max}})
    except Exception as e:
        print('/terrain_upload:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

