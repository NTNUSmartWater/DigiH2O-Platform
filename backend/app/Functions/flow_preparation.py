import os, traceback, json, shutil, pickle
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from Functions import functions, flowFunctions
from config import PROJECT_STATIC_ROOT



router = APIRouter()

@router.post("/terrain_upload")
async def terrain_upload(file: UploadFile = File(...), projectName: str = Form(...),
                         user=Depends(functions.basic_auth)):
    try:
        project_name, _ = functions.project_definer(projectName, user)
        save_dir = os.path.join(PROJECT_STATIC_ROOT, project_name, "terrains")
        if not os.path.exists(save_dir): os.makedirs(save_dir)
        path = os.path.normpath(os.path.join(save_dir, file.filename.split('.')[0] + '.pkl'))
        if not os.path.exists(path):
            terrain_path = os.path.normpath(os.path.join(save_dir, file.filename))
            if not os.path.exists(terrain_path):
                with open(terrain_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
            polygon = flowFunctions.terrain_reader(terrain_path)
            with open(path, "wb") as f:
                pickle.dump(polygon, f)
            functions.safe_remove(terrain_path)
        else: polygon = pickle.load(open(path, 'rb'))
        min, max = polygon['value'].values.min(), polygon['value'].values.max()
        print(min, max, polygon)
        content = {'min': min, 'max': max, 'polygon': json.loads(polygon.to_json())}
        return JSONResponse({'status': 'ok', 'content': content})
    except Exception as e:
        print('/terrain_upload:\n==============')
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f"Error: {e}"})

