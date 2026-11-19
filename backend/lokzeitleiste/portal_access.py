"""Authenticated TF login/page telemetry for the temporary administration test tile."""
from pathlib import Path
import re
from zoneinfo import ZoneInfo
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import database_session
from .models import TfPortalAccess, TfProfile, User
from .tf_portal import driver_dependency
from .accounts.access import demand


def record(db, user, version='', event='login', path=''):
    if user.role != 'tf': return
    version = version if re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version or '') and len(version)<=32 else ''
    db.add(TfPortalAccess(user_id=user.id,android_version=version,event=event,path=path))


class Visit(BaseModel):
    path: str = Field(max_length=160)
    android_version: str = Field(default='',max_length=32)


def create_router(require_account, require_admin):
    router=APIRouter()
    driver=driver_dependency(require_account)
    @router.post('/api/v1/tf/portal-access',status_code=204)
    def visit(data:Visit,user=Depends(driver),db:Session=Depends(database_session)):
        # Only path names, never search strings, personal text or tokens.
        if not re.fullmatch(r'/tf(?:/[a-z0-9-]+)*',data.path): raise HTTPException(422)
        record(db,user,data.android_version,'page',data.path)
        db.commit()
    @router.get('/api/v1/admin/portal-access')
    def rows(user=Depends(require_admin),db:Session=Depends(database_session)):
        demand(db,user,'portal_access',1)
        result=[]
        query=select(TfPortalAccess,User,TfProfile).join(User,User.id==TfPortalAccess.user_id).join(TfProfile,TfProfile.user_id==User.id).order_by(TfPortalAccess.id.desc()).limit(500)
        for row,tf,profile in db.execute(query):
            stamp=row.occurred_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Europe/Berlin'))
            result.append(dict(tf_number=tf.username,last_name=profile.last_name,first_name=profile.first_name,date=stamp.strftime('%d.%m.%Y'),time=stamp.strftime('%H:%M:%S'),android_version=row.android_version))
        return result
    @router.get('/admin/portal-access')
    def page(): return FileResponse(Path(__file__).parent/'static/portal-access.html',headers={'Cache-Control':'no-store'})
    @router.get('/admin/portal-access.js')
    def script(): return FileResponse(Path(__file__).parent/'static/portal-access.js',media_type='text/javascript')
    return router
