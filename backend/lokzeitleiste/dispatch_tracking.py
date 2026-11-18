"""Dispatcher management pages and consent-filtered live train tracking."""
from pathlib import Path
from fastapi import APIRouter,Depends,Response
from fastapi.responses import HTMLResponse,FileResponse
from sqlalchemy.orm import Session
from .db import database_session
from .gps_preferences import shared_positions
STATIC=Path(__file__).parent/'static'

def create_router(require_admin):
    router=APIRouter()
    @router.get('/admin/dispatchers')
    @router.get('/admin/dispatchers/new')
    def dispatchers():
        page=(STATIC/'staff.html').read_text()
        page=page.replace("{{backend_staff.text_045e24cbddab}}","{{dispatch_tracking.text_640480716e00}}")
        page=page.replace("{{backend_staff.text_ae186dd21359}}","{{dispatch_tracking.text_640480716e00}}")
        page=page.replace("{{backend_staff.text_a3d928778935}}","{{dispatch_tracking.text_640480716e00}}")
        page=page.replace("{{backend_staff.text_0f51c3a734c4}}","{{dispatch_tracking.text_11507a0e2f5e}}")
        return HTMLResponse(page,headers={'Cache-Control':'no-cache'})
    @router.get('/admin/tracking')
    def page():return FileResponse(STATIC/'train-tracking.html',headers={'Cache-Control':'no-cache'})
    @router.get('/admin/train-tracking.js')
    def script():return FileResponse(STATIC/'train-tracking.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/api/v1/admin/tracking/positions')
    def positions(response:Response,actor=Depends(require_admin),db:Session=Depends(database_session)):
        response.headers['Cache-Control']='private, no-store'
        data=shared_positions(db)
        data['positions']=[{key:value for key,value in point.items() if key in ('id','lat','lon','t','train_number','first_name')} for point in data['positions']]
        return data
    return router
