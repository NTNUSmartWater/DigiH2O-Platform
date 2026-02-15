import os, traceback, json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from Functions import functions



router = APIRouter()

# @router.post("/init_lakes")
# async def init_lakes(request: Request, user=Depends(functions.basic_auth)):
#     try:
#         pass

#     except Exception as e:
#         print('/init_lakes:\n==============')
#         traceback.print_exc()
#         return JSONResponse({'status': 'error', 'message': f"Error: {e}"})
