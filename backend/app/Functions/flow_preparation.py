import os, traceback, json, shutil, io, mercantile, rasterio
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, Response
from fastapi.responses import JSONResponse
from Functions import functions, flowFunctions
from config import PROJECT_STATIC_ROOT
import numpy as np, matplotlib.cm as cm
import geopandas as gpd, pandas as pd
from PIL import Image
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
from rasterio.features import shapes
from shapely.geometry import shape

router = APIRouter()

@router.get("/{name}/terrain/{key}/{folder}/{filename}/{z}/{x}/{y}.png")
def terrain_tiles(name: str, key: str, folder: str, filename: str, z: int, x: int, y: int):
    try:
        project = name.replace("*", "/")
        tif_folder = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project, "terrains", folder))
        tif_path = os.path.normpath(os.path.join(tif_folder, filename))
        # Get min and max
        with open(os.path.normpath(os.path.join(tif_folder, f"{folder}.json"))) as f:
            meta = json.load(f)
        global_min, global_max = float(meta[key].get("min", 0)), float(meta[key].get("max", 0))
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
        meta_path, meta = os.path.splitext(terrain_path)[0] + ".json", {}
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f: meta = json.load(f)
        meta['raw'] = {"min": global_min, "max": global_max}
        with open(meta_path, "w") as f: json.dump(meta, f)
        new_name = project_name.replace("/", "*")
        tile_url = f"/{new_name}/terrain/raw/{name}/{os.path.basename(cog_path)}/{{z}}/{{x}}/{{y}}.png"
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
        meta_path, meta = os.path.normpath(os.path.join(dir, json_file)), {}
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f: meta = json.load(f)
        meta['filled'] = {"min": global_min, "max": global_max}
        with open(meta_path, "w") as f: json.dump(meta, f)
        new_name = project_name.replace("/", "*")
        tile_url = f"/{new_name}/terrain/filled/{folder}/{fill_name}/{{z}}/{{x}}/{{y}}.png"
        contents = {"tile_url": tile_url, "min": global_min, "max": global_max}
        return JSONResponse({'status': 'ok', 'content': contents})
    except Exception as e:
        print('/fill_terrain:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/raster_check")
async def raster_check(request: Request, user=Depends(functions.basic_auth)):
    body = await request.json()
    file_name, key = body.get('filename'), body.get('key')
    folder = file_name.rstrip(".tif")
    project_name, _ = functions.project_definer(body.get('projectName'), user)
    dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains", folder))
    if key == "fill":
        status, message = "error", 'No fill terrain found. Please upload terrain data and run "Fill sinks/depressions".'
        path = os.path.normpath(os.path.join(dir, folder + "_filled.tif"))
    elif key == "flow_direction":
        status, message = "error", 'No flow direction found. Work on "Terrain Processing" and run "Flow direction".'
        path = os.path.normpath(os.path.join(dir, folder + "_flowdir.tif"))
    elif key == "flow_accumulation":
        status, message = "error", 'No flow accumulation found. Work on "Terrain Processing" and run "Flow accumulation".'
        path = os.path.normpath(os.path.join(dir, folder + "_flowacc.tif"))
    if os.path.exists(path): status, message = "ok", ''
    return JSONResponse({'status': status, 'message': message})

@router.post("/flow_direction")
async def flow_direction(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        file_name = body.get('filename')
        folder = file_name.rstrip(".tif")
        flowdir_name, json_file = folder + "_flowdir.tif", f"{folder}.json"
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains", folder))
        fill_path = os.path.normpath(os.path.join(dir, folder + "_filled.tif"))
        flow_path = os.path.normpath(os.path.join(dir, flowdir_name))
        if os.path.exists(flow_path): functions.safe_remove(flow_path)
        flowFunctions.flow_direction(fill_path, flow_path)
        with rasterio.open(flow_path) as src:
            data = src.read(1, masked=True)
            global_min, global_max = float(data.min()), float(data.max())
        meta_path, meta = os.path.normpath(os.path.join(dir, json_file)), {}
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f: meta = json.load(f)
        meta['flowdir'] = {"min": global_min, "max": global_max}
        with open(meta_path, "w") as f: json.dump(meta, f)
        new_name = project_name.replace("/", "*")
        tile_url = f"/{new_name}/terrain/flowdir/{folder}/{flowdir_name}/{{z}}/{{x}}/{{y}}.png"
        contents = {"tile_url": tile_url, "min": global_min, "max": global_max}
        return JSONResponse({'status': 'ok', 'content': contents})
    except Exception as e:
        print('/flow_direction:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/flow_accumulation")
async def flow_accumulation(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        file_name = body.get('filename')
        folder = file_name.rstrip(".tif")
        flowdir_name, flowacc_name = f"{folder}_flowdir.tif", f"{folder}_flowacc.tif"
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains", folder))
        flowdir_path = os.path.normpath(os.path.join(dir, flowdir_name))
        flowacc_path = os.path.normpath(os.path.join(dir, flowacc_name))
        if os.path.exists(flowacc_path): functions.safe_remove(flowacc_path)
        flowFunctions.flow_accumulation(flowdir_path, flowacc_path)
        with rasterio.open(flowacc_path) as src:
            data = src.read(1, masked=True)
            global_min, global_max = float(data.min()), float(data.max())
        meta_path, meta = os.path.normpath(os.path.join(dir, f"{folder}.json")), {}
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f: meta = json.load(f)
        meta['flowacc'] = {"min": global_min, "max": global_max}
        with open(meta_path, "w") as f: json.dump(meta, f)
        new_name = project_name.replace("/", "*")
        tile_url = f"/{new_name}/terrain/flowacc/{folder}/{flowacc_name}/{{z}}/{{x}}/{{y}}.png"
        contents = {"tile_url": tile_url, "min": global_min, "max": global_max}
        return JSONResponse({'status': 'ok', 'content': contents})
    except Exception as e:
        print('/flow_accumulation:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/catchment")
async def catchment(request: Request, user=Depends(functions.basic_auth)):
    try:
        body = await request.json()
        file_name, lat, lon = body.get('filename'), body.get('lat'), body.get('lon')
        threshold, snap_distance = float(body.get('threshold')), float(body.get('snapDistance'))
        folder = file_name.rstrip(".tif")
        flowdir_name, flowacc_name = f"{folder}_flowdir.tif", f"{folder}_flowacc.tif"
        catchment_name = f"{folder}_catchment.tif"
        project_name, _ = functions.project_definer(body.get('projectName'), user)
        dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains", folder))
        flowdir_path = os.path.normpath(os.path.join(dir, flowdir_name))
        flowacc_path = os.path.normpath(os.path.join(dir, flowacc_name))
        catchment_path = os.path.normpath(os.path.join(dir, catchment_name))
        if os.path.exists(catchment_path): functions.safe_remove(catchment_path)
        catchment = flowFunctions.watershed(flowdir_path, flowacc_path, lat, lon, threshold, snap_distance)
        if catchment.empty: return JSONResponse({'status': 'error', 'message': 'No catchment found.'})
        return JSONResponse({'status': 'ok', 'content': json.loads(catchment.to_json())})
    except Exception as e:
        print('/catchment:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/catchment_upload")
async def catchment_upload(file: UploadFile = File(...)):
    try:
        gdf = gpd.read_file(file.file)
        if gdf.empty: return JSONResponse({'status': 'error', 'message': 'No catchment data found.'})
        if gdf.crs != "EPSG:4326": gdf = gdf.to_crs("EPSG:4326")
        return JSONResponse({'status': 'ok', 'content': json.loads(gdf.to_json())})
    except Exception as e:
        print('/catchment_export:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/soil_upload")
async def soil_upload(file: UploadFile = File(...), projectName: str = Form(...),
                         user=Depends(functions.basic_auth)):
    try:
        project_name, _ = functions.project_definer(projectName, user)
        dir = os.path.normpath(os.path.join(PROJECT_STATIC_ROOT, project_name, "soils"))
        os.makedirs(dir, exist_ok=True)
        file_ext = file.filename.split(".")
        save_dir = os.path.normpath(os.path.join(dir, file_ext[0]))
        if os.path.exists(save_dir): shutil.rmtree(save_dir)
        os.makedirs(save_dir, exist_ok=True)
        soil_path = os.path.normpath(os.path.join(save_dir, file.filename))
        with open(soil_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        if file_ext[-1].lower() in ["tif"]:
            with rasterio.open(soil_path) as src:
                data = src.read(1)
                mask = data != src.nodata
                data = data.astype(np.int32)
                results = ({"geometry": shape(geom), "soil": flowFunctions.soil_codes.get(value, "")}
                    for geom, value in shapes(data, mask=mask, transform=src.transform))
                geoms = list(results)
            soil_data = gpd.GeoDataFrame(geoms, crs=src.crs)
        elif file_ext[-1].lower() in ["geojson"]: soil_data = gpd.read_file(soil_path)
        if soil_data.empty: return JSONResponse({'status': 'error', 'message': 'No soil data found.'})        
        if '_id' not in soil_data.columns: soil_data.insert(0, '_id', range(1, len(soil_data) + 1))
        if 'soil' in soil_data.columns:
            new_cols = ["theta_s", "theta_r", "k_sat_ver", "soil_depth", "conductivity_decay", "brooks_corey"]
            soil_data[new_cols] = soil_data['soil'].map(flowFunctions.soil_types).apply(pd.Series)
        else: soil_data['soil'] = 'Unknown'
        if soil_data.crs != "EPSG:4326": soil_data = soil_data.to_crs("EPSG:4326")
        return JSONResponse({'status': 'ok', 'content': json.loads(soil_data.to_json())})
    except Exception as e:
        print('/soil_upload:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/polygon_clip")
async def polygon_clip(request: Request):
    try:
        body = await request.json()
        base_layer, clip_layer = body.get('baseLayer'), body.get('clipLayer')
        base_layer = gpd.GeoDataFrame.from_features(base_layer, crs="EPSG:4326")
        clip_layer = gpd.GeoDataFrame.from_features(clip_layer, crs="EPSG:4326")
        # Clip the base layer to the clip layer
        clipped_layer = gpd.clip(base_layer, clip_layer)
        if clipped_layer.empty: return JSONResponse({'status': 'error', 'message': 'No data found.'})
        clipped_layer = clipped_layer.reset_index(drop=True)
        clipped_layer['_id'] = clipped_layer.index + 1
        return JSONResponse({'status': 'ok', 'content': json.loads(clipped_layer.to_json())})
    except Exception as e:
        print('/polygon_clip:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

@router.post("/assign_soil_type")
async def assign_soil_type(request: Request):
    try:
        body = await request.json()
        soil_type = body.get('soilType')
        content = flowFunctions.soil_type[soil_type]
        content.insert(0, soil_type)
        return JSONResponse({'status': 'ok', 'content': content})
    except Exception as e:
        print('/assign_soil_type:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})



