"""Independent wagon inspector personnel administration; no TF profile on creation."""
import json
from datetime import date,datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import FileResponse,Response
from pydantic import BaseModel,ConfigDict,Field,EmailStr,model_validator,field_validator
from sqlalchemy import select,delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import database_session
from .models import User,WgmProfile,WgmAddress,TfProfile,TfEmployment,TfIdentity,TfAddress,EmployeeCategory,AccountPolicy,ProfilePhoto,SessionToken
from .schemas import TfAddressIn
from .security import hash_password
from .user_directories import directory_transaction
from .accounts.photos import decode_photo,save_photo
from .localization import source

KEYS={'title': 'wgm.text_159c423d8698', 'new': 'wgm.text_f238a1eac3a5', 'intro': 'wgm.text_7978b29e28a0', 'first_name': 'wgm.text_9f9375b3158c', 'last_name': 'wgm.text_9966aefa9d77', 'personnel_number': 'wgm.text_4a84e5284bdc', 'username': 'wgm.text_679c6fde730c', 'password': 'wgm.text_83fc92a0ba29', 'email': 'wgm.text_fa75b34eb831', 'birth_date': 'wgm.text_62d823660ce7', 'vacation_days': 'wgm.text_39ecd01bafd5', 'weekly_hours': 'wgm.text_e5ce36cd2280', 'entry_date': 'wgm.text_95733ec34595', 'exit_date': 'wgm.text_61e3c32890ee', 'immediate_block': 'wgm.text_ec8a54f4a783', 'nationality': 'wgm.text_2b36d5d00974', 'gender': 'wgm.text_294e5df41e85', 'unspecified': 'wgm.text_e48b14b731f6', 'male': 'wgm.text_80d5c9944c8e', 'female': 'wgm.text_a4b50dd5e879', 'diverse': 'wgm.text_f7d19c7b0943', 'addresses': 'wgm.text_bc1f400ddfaf', 'street': 'wgm.text_4089cfbdf642', 'house_number': 'wgm.text_a7ff2a8de57f', 'postal_code': 'wgm.text_8250292ca38d', 'city': 'wgm.text_c3b9eb475f0e', 'federal_state': 'wgm.text_dd890e085b37', 'is_postal': 'wgm.text_6402320e9f5f', 'add_address': 'wgm.text_8852f2a232fe', 'remove': 'wgm.text_c7d21c88c12e', 'view': 'wgm.text_61e216662c1b', 'edit': 'wgm.text_7f9e1d04f7ff', 'save': 'wgm.text_9317b0cd6349', 'close': 'wgm.text_6b5667c9df74', 'search': 'wgm.text_952b39381680', 'empty': 'wgm.text_cbe4f752ca7a', 'error': 'wgm.text_93cdee45df0e', 'saved': 'wgm.text_6806ae8b2d7b', 'conflict': 'wgm.text_7519dcd7f53b', 'not_found': 'wgm.text_6fc40f9d8988', 'invalid': 'wgm.text_c84c0adcc336', 'photo': 'wgm.text_3bc1afae6bd4', 'photo_clear': 'wgm.text_1b69a8e48933', 'h49': 'wgm.text_73b2e03563d8'}
STATIC=Path(__file__).parent/'static'
COUNTRIES=json.loads((Path(__file__).parent/'accounts'/'countries.json').read_text())
FIELDS=('first_name','last_name','personnel_number','birth_date','vacation_days','email','gender','nationality','weekly_minutes','entry_date','exit_date','immediate_block')


def message(key):return source(KEYS[key])


class WgmIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    first_name:str=Field(min_length=1,max_length=120)
    last_name:str=Field(min_length=1,max_length=120)
    personnel_number:str=Field(min_length=1,max_length=40)
    birth_date:date
    vacation_days:int=Field(ge=0,le=366)
    email:EmailStr
    gender:str=Field(pattern=r'^(male|female|diverse|unspecified)$')
    nationality:str=Field(pattern=r'^[A-Z]{2}$')
    weekly_minutes:int=Field(ge=0,le=10080)
    entry_date:date
    exit_date:date|None=None
    immediate_block:bool=False
    addresses:list[TfAddressIn]=Field(min_length=1,max_length=10)
    photo_base64:str|None=Field(default=None,max_length=6990510)

    @field_validator('first_name','last_name','personnel_number')
    @classmethod
    def clean(cls,value):
        if not value.strip():raise ValueError(message('invalid'))
        return value.strip()

    @model_validator(mode='after')
    def valid(self):
        if len(self.addresses)==1:self.addresses[0].is_postal=True
        if self.nationality not in COUNTRIES or self.birth_date>datetime.now(ZoneInfo('Europe/Berlin')).date() or self.exit_date and self.exit_date<self.entry_date or sum(a.is_postal for a in self.addresses)!=1:
            raise ValueError(message('invalid'))
        return self


class WgmCreate(WgmIn):
    username:str=Field(pattern=r'^[a-z0-9][a-z0-9._-]{2,63}$')
    password:str=Field(min_length=6,max_length=4096)


class WgmUpdate(WgmIn):
    username:str=Field(pattern=r'^[a-z0-9][a-z0-9._-]{2,63}$')


def migrate_existing_wgm(db):
    """Preserve IDs, credentials, reports and archives; move files with rollback.

    Historic TF companion rows remain as report history, never the WGM master data.
    One transaction per person; a failed filesystem or DB move stops safely.
    """
    users=db.scalars(select(User).join(EmployeeCategory,EmployeeCategory.user_id==User.id).where(User.role=='tf',EmployeeCategory.category=='wgm').order_by(User.id)).all()
    for user in users:
        old=db.get(TfProfile,user.id)
        if not old:raise RuntimeError(message('not_found'))
        if db.get(WgmProfile,user.id):raise RuntimeError(message('conflict'))
        employment=db.get(TfEmployment,user.id);identity=db.get(TfIdentity,user.id)
        values={name:getattr(old,name) for name in ('first_name','last_name','personnel_number','birth_date','vacation_days','email')}
        values.update(gender=identity.gender if identity else old.gender or 'unspecified',nationality=employment.nationality if employment else None,weekly_minutes=employment.weekly_minutes if employment else 2400,entry_date=employment.entry_date if employment else None,exit_date=employment.exit_date if employment else None,immediate_block=employment.immediate_block if employment else False)
        db.add(WgmProfile(user_id=user.id,**values));db.flush()
        for address in db.scalars(select(TfAddress).where(TfAddress.user_id==user.id)):
            db.add(WgmAddress(user_id=user.id,**{key:getattr(address,key) for key in ('street','house_number','postal_code','city','federal_state','is_postal')}))
        user.role='wgm'
        db.execute(delete(SessionToken).where(SessionToken.user_id==user.id))
        try:
            with directory_transaction(user,user.username,previous_role='tf'):db.commit()
        except BaseException:
            db.rollback();raise


def create_router(require_admin):
    def no_store(response:Response):response.headers['Cache-Control']='private, no-store'
    router=APIRouter(dependencies=[Depends(no_store)])

    def find(db,user_id,lock=False):
        query=select(User).where(User.id==user_id,User.role=='wgm')
        user=db.scalar(query.with_for_update() if lock else query)
        profile=db.get(WgmProfile,user_id)
        if not user or not profile:raise HTTPException(404,message('not_found'))
        return user,profile

    def view(db,user,profile):
        return dict(id=user.id,username=user.username,**{name:getattr(profile,name) for name in FIELDS},has_photo=db.get(ProfilePhoto,user.id) is not None,addresses=[{key:getattr(row,key) for key in ('street','house_number','postal_code','city','federal_state','is_postal')} for row in db.scalars(select(WgmAddress).where(WgmAddress.user_id==user.id).order_by(WgmAddress.id))])

    def store(db,user,profile,data):
        for key in FIELDS:setattr(profile,key,str(data.email).lower() if key=='email' else getattr(data,key))
        db.execute(delete(WgmAddress).where(WgmAddress.user_id==user.id))
        for address in data.addresses:db.add(WgmAddress(user_id=user.id,**address.model_dump()))
        from .employee_mail import save_email
        save_email(db,user,str(data.email),data.password if isinstance(data,WgmCreate) else None)
        save_photo(db,user.id,decode_photo(data.photo_base64))

    @router.get('/admin/wgm')
    @router.get('/admin/wgm/new')
    def page():return FileResponse(STATIC/'wgm.html')

    @router.get('/admin/wgm.js')
    def script():return FileResponse(STATIC/'wgm.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})

    @router.get('/api/v1/admin/wgm/metadata')
    def metadata(user=Depends(require_admin)):
        return dict(countries=COUNTRIES,today=datetime.now(ZoneInfo('Europe/Berlin')).date().isoformat())

    @router.get('/api/v1/admin/wgm')
    def listing(user=Depends(require_admin),db:Session=Depends(database_session)):
        return [view(db,u,p) for u,p in db.execute(select(User,WgmProfile).join(WgmProfile,WgmProfile.user_id==User.id).where(User.role=='wgm').order_by(WgmProfile.last_name,WgmProfile.first_name,User.id))]

    @router.get('/api/v1/admin/wgm/{user_id}')
    def read(user_id:int,user=Depends(require_admin),db:Session=Depends(database_session)):
        return view(db,*find(db,user_id))

    @router.get('/api/v1/admin/wgm/{user_id}/photo')
    def photo(user_id:int,user=Depends(require_admin),db:Session=Depends(database_session)):
        find(db,user_id);row=db.get(ProfilePhoto,user_id)
        if not row:raise HTTPException(404,message('not_found'))
        return Response(row.image_data,media_type='image/jpeg',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

    @router.post('/api/v1/admin/wgm',status_code=201)
    def create(data:WgmCreate,actor=Depends(require_admin),db:Session=Depends(database_session)):
        try:
            user=User(username=data.username,password_hash=hash_password(data.password),role='wgm');db.add(user);db.flush()
            profile=WgmProfile(user_id=user.id);db.add(profile)
            # Populate scalar fields before an autoflush can check NOT NULL constraints.
            for key in FIELDS:setattr(profile,key,str(data.email).lower() if key=='email' else getattr(data,key))
            db.add(AccountPolicy(user_id=user.id,must_change_password=True));store(db,user,profile,data)
            with directory_transaction(user,creating=True):db.commit()
            return view(db,user,profile)
        except IntegrityError:
            db.rollback();raise HTTPException(409,message('conflict'))

    @router.put('/api/v1/admin/wgm/{user_id}')
    def update(user_id:int,data:WgmUpdate,actor=Depends(require_admin),db:Session=Depends(database_session)):
        user,profile=find(db,user_id,True);previous=user.username
        try:
            user.username=data.username;store(db,user,profile,data)
            with directory_transaction(user,previous):db.commit()
            return view(db,user,profile)
        except IntegrityError:
            db.rollback();raise HTTPException(409,message('conflict'))

    return router
