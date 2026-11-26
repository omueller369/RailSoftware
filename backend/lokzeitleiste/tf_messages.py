# Gemeinsame Verarbeitung für Nachrichten und die gemeinsame Kommunikation.
"""TF-to-TF inbox. No SMTP, usernames or TF numbers in message-facing responses."""
from .localization import source as _text_source, resolve_placeholders
import io
from pathlib import Path,PurePosixPath
from fastapi import APIRouter,Depends,File,Form,UploadFile,HTTPException,Query
from fastapi.responses import FileResponse,Response
from pydantic import BaseModel,Field,ValidationError,field_validator
from sqlalchemy import select,func,or_,and_,case
from sqlalchemy.orm import Session
from PIL import Image
from .db import database_session
from .models import StaffProfile,User,TfProfile,TfMessage as Message,TfMessageDelivery as Delivery,TfMessageAttachment as Attachment,TfChatGroup as ChatGroup,TfChatMember as Member,TfChatMessage as GroupMessage,now_utc
from .security import account_active
from .accounts.access import ready

MAX_FILE=10*1024*1024
class Recipients(BaseModel):
    recipients:list[int]=Field(default_factory=list,max_length=5000)
    all_tf:bool=False
class GroupIn(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    members:list[int]=Field(min_length=1,max_length=499)

class MessageIn(Recipients):
    group_id:int|None=Field(default=None,ge=1)
    subject:str=Field(min_length=1,max_length=200)
    body:str=Field(min_length=1,max_length=1000)
    @field_validator('subject','body')
    @classmethod
    def nonempty(cls,value):
        value=value.strip()
        if not value:raise ValueError(_text_source('server_tf_messages.text_ad0dcaacfb85'))
        return value
class ReadIn(BaseModel):read:bool

def name(profile):
    if not profile:raise HTTPException(404,_text_source('server_tf_messages.text_a8c327fb1b2a'))
    return (profile.first_name+' '+profile.last_name).strip()
def identity(db,user):
    profile=db.get(TfProfile if user.role=='tf' else StaffProfile,user.id)
    return name(profile) if profile else _text_source('server_tf_messages.text_4b42c6690ebe')
def recipients(db):
    rows=[]
    for u in db.scalars(select(User).where(User.role.in_(['tf','staff','admin']),User.active==True)):
        if account_active(db,u):rows.append((u,identity(db,u)))
    return sorted(rows,key=lambda row:(row[0].role=='tf',row[1].casefold(),row[0].id))

def targets(db,data):
    active={u.id for u,p in recipients(db)};selected={u.id for u,p in recipients(db) if u.role=='tf'} if data.all_tf else set(data.recipients)
    if not selected:raise HTTPException(422,_text_source('server_tf_messages.text_181d7c8b6aa2'))
    if not selected<=active:raise HTTPException(422,_text_source('server_tf_messages.text_753d6cdca15d'))
    return selected

def owned(db,user,message_id):
    delivery=db.scalar(select(Delivery).where(Delivery.message_id==message_id,Delivery.recipient_id==user.id,Delivery.deleted_at.is_(None)).with_for_update())
    if not delivery:raise HTTPException(404,_text_source('server_tf_messages.text_6d0ff17167bf'))
    return delivery,db.get(Message,message_id)

def view(db,message,delivery,detail=False):
    file=db.get(Attachment,message.attachment_id) if detail and message.attachment_id else None
    result=dict(id=message.id,sender_name=message.sender_name,subject=message.subject,created_at=message.created_at.isoformat()+'Z',read=delivery.read_at is not None,has_attachment=message.attachment_id is not None)
    if detail:result.update(body=message.body,attachment=dict(filename=file.filename,mime_type=file.mime_type,size=len(file.content),url=f'/api/v1/tf/messages/{message.id}/attachment') if file else None)
    return result


def sent_owned(db,user,message_id):
    message=db.scalar(select(Message).where(Message.id==message_id,Message.sender_id==user.id))
    if not message:raise HTTPException(404,_text_source('server_tf_messages.text_6d0ff17167bf'))
    return message

def sent_view(db,message,detail=False):
    names=[identity(db,u) for u in db.scalars(select(User).join(Delivery,Delivery.recipient_id==User.id).where(Delivery.message_id==message.id).order_by(User.id))]
    result=dict(id=message.id,subject=message.subject,sender_name=message.sender_name,recipient_names=names,created_at=message.created_at.isoformat()+'Z',has_attachment=message.attachment_id is not None)
    if detail:
        file=db.get(Attachment,message.attachment_id) if message.attachment_id else None
        result.update(body=message.body,attachment=dict(filename=file.filename,mime_type=file.mime_type,size=len(file.content),url=f'/api/v1/tf/messages/sent/{message.id}/attachment') if file else None)
    return result

def create_router(require_account):
    router=APIRouter()
    def driver(user=Depends(require_account),db:Session=Depends(database_session)):
        if user.role not in ('tf','staff','admin'):raise HTTPException(403,_text_source('server_tf_messages.text_aab4a4512402'))
        ready(db,user)
        return user
    @router.get('/admin/messages')
    def backend_page():
        content=resolve_placeholders((Path(__file__).parent/'static'/'tf-messages.html').read_text())
        content=content.replace('TF-Portal',_text_source('server_tf_messages.text_2456bb8ed72f')).replace('<header><h1>Verwaltung</h1></header>','<header><a href="/admin/start">Verwaltung</a></header>').replace('</body>','<script src="/admin/backend-nav.js"></script></body>')
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content,headers={'Cache-Control':'no-store'})
    @router.get('/tf/chat.js')
    def chat_script():return FileResponse(Path(__file__).parent/'static'/'tf-chat.js',media_type='text/javascript')
    @router.get('/tf/chat.css')
    def chat_styles():return FileResponse(Path(__file__).parent/'static'/'tf-chat.css',media_type='text/css')
    @router.get('/tf/messages.js')
    def script():return FileResponse(Path(__file__).parent/'static'/'tf-messages.js',media_type='text/javascript',headers={'Cache-Control':'no-cache'})
    @router.get('/api/v1/tf/messages/recipients')
    def choices(user=Depends(driver),db:Session=Depends(database_session)):return [dict(id=u.id,name=p,group='TF' if u.role=='tf' else _text_source('server_tf_messages.text_3587543eb803')) for u,p in recipients(db)]
    def direct_query(user_id,peer=None):
        # Gruppennachrichten bleiben im Posteingang und werden nicht als private Chats ausgegeben.
        count=select(func.count()).select_from(Delivery).where(Delivery.message_id==Message.id).correlate(Message).scalar_subquery()
        query=select(Message,Delivery).join(Delivery,Delivery.message_id==Message.id).where(count==1,~select(GroupMessage.message_id).where(GroupMessage.message_id==Message.id).exists())
        incoming=and_(Delivery.recipient_id==user_id,Delivery.deleted_at.is_(None))
        outgoing=Message.sender_id==user_id
        if peer is not None:
            incoming=and_(incoming,Message.sender_id==peer);outgoing=and_(outgoing,Delivery.recipient_id==peer)
        return query.where(or_(incoming,outgoing))
    def group_owned(db,user,group_id):
        group=db.get(ChatGroup,group_id)
        if not group or not db.get(Member,(group_id,user.id)):
            raise HTTPException(404,_text_source('chat_groups.text_4a47ee5a8057'))
        return group
    @router.post('/api/v1/tf/messages/groups',status_code=201)
    def create_group(data:GroupIn,user=Depends(driver),db:Session=Depends(database_session)):
        label=data.name.strip();members=set(data.members)|{user.id}
        active={u.id for u,_ in recipients(db)}
        if not label or len(members)<2 or not members<=active:
            raise HTTPException(422,_text_source('chat_groups.text_4a47ee5a8057'))
        group=ChatGroup(name=label,creator_id=user.id);db.add(group);db.flush()
        for member in members:db.add(Member(group_id=group.id,user_id=member))
        db.commit();return dict(id=group.id,name=group.name,kind='group',unread=0)
    @router.get('/api/v1/tf/messages/groups')
    def groups(user=Depends(driver),db:Session=Depends(database_session)):
        result=[]
        for group in db.scalars(select(ChatGroup).join(Member,Member.group_id==ChatGroup.id).where(Member.user_id==user.id)):
            row=db.execute(select(func.max(Message.created_at),func.count(Message.id),func.sum(case((and_(Delivery.read_at.is_(None),Message.sender_id!=user.id),1),else_=0))).select_from(GroupMessage).join(Message,Message.id==GroupMessage.message_id).outerjoin(Delivery,and_(Delivery.message_id==Message.id,Delivery.recipient_id==user.id,Delivery.deleted_at.is_(None))).where(GroupMessage.group_id==group.id,or_(Message.sender_id==user.id,Delivery.id.is_not(None)))).one()
            result.append(dict(id=group.id,name=group.name,kind='group',last_at=(row[0] or group.created_at).isoformat()+'Z',count=row[1],unread=int(row[2] or 0)))
        return result
    @router.get('/api/v1/tf/messages/groups/{group_id}')
    def group_conversation(group_id:int,before:int|None=Query(default=None,ge=1),q:str=Query(default='',max_length=200),user=Depends(driver),db:Session=Depends(database_session)):
        group_owned(db,user,group_id)
        query=select(Message,Delivery).join(GroupMessage,GroupMessage.message_id==Message.id).outerjoin(Delivery,and_(Delivery.message_id==Message.id,Delivery.recipient_id==user.id)).where(GroupMessage.group_id==group_id,or_(Message.sender_id==user.id,and_(Delivery.id.is_not(None),Delivery.deleted_at.is_(None))))
        if before:query=query.where(Message.id<before)
        if q:query=query.where(Message.body.contains(q,autoescape=True))
        rows=db.execute(query.order_by(Message.id.desc()).limit(51)).all();items=[]
        for message,delivery in reversed(rows[:50]):
            mine=message.sender_id==user.id
            if not mine and delivery.read_at is None:delivery.read_at=now_utc()
            value=sent_view(db,message,True) if mine else view(db,message,delivery,True)
            # Eine Gruppen-Lesebestätigung gilt erst, wenn alle Empfänger gelesen haben.
            unread=db.scalar(select(func.count()).select_from(Delivery).where(Delivery.message_id==message.id,Delivery.read_at.is_(None),Delivery.deleted_at.is_(None))) if mine else 0
            value.update(mine=mine,read=not unread);items.append(value)
        db.commit();return dict(messages=items,more=len(rows)>50)
    @router.get('/api/v1/tf/messages/chats')
    def chats(user=Depends(driver),db:Session=Depends(database_session)):
        query=direct_query(user.id).with_only_columns(Message.id,Message.sender_id,Delivery.recipient_id,Delivery.read_at,Message.created_at).subquery()
        peer=func.coalesce(func.nullif(query.c.sender_id,user.id),query.c.recipient_id)
        rows=db.execute(select(peer.label('peer'),func.max(query.c.created_at).label('last_at'),func.count().label('count'),func.sum(case((and_(query.c.recipient_id==user.id,query.c.read_at.is_(None)),1),else_=0)).label('unread')).group_by(peer)).all()
        active={u.id:label for u,label in recipients(db)}
        return [dict(peer_id=r.peer,name=active.get(r.peer,_text_source('server_tf_messages.text_4b42c6690ebe')),unread=r.unread,last_at=r.last_at.isoformat()+'Z',count=r.count) for r in rows if r.peer!=user.id]
    @router.get('/api/v1/tf/messages/chats/{peer_id}')
    def conversation(peer_id:int,before:int|None=Query(default=None,ge=1),q:str=Query(default='',max_length=200),user=Depends(driver),db:Session=Depends(database_session)):
        if not db.get(User,peer_id):raise HTTPException(404,_text_source('server_tf_messages.text_a8c327fb1b2a'))
        query=direct_query(user.id,peer_id)
        if before:query=query.where(Message.id<before)
        if q:query=query.where(Message.body.contains(q,autoescape=True))
        rows=db.execute(query.order_by(Message.id.desc()).limit(51)).all();more=len(rows)>50;items=[]
        for message,delivery in reversed(rows[:50]):
            mine=message.sender_id==user.id
            if not mine and delivery.read_at is None:delivery.read_at=now_utc()
            value=sent_view(db,message,True) if mine else view(db,message,delivery,True)
            value.update(mine=mine,read=delivery.read_at is not None);items.append(value)
        db.commit();return dict(messages=items,more=more)
    @router.get('/api/v1/tf/messages/unread')
    def unread(user=Depends(driver),db:Session=Depends(database_session)):
        return dict(count=db.scalar(select(func.count()).select_from(Delivery).join(Message,Message.id==Delivery.message_id).where(Delivery.recipient_id==user.id,Message.sender_id!=user.id,Delivery.read_at.is_(None),Delivery.deleted_at.is_(None))))
    @router.get('/api/v1/tf/messages')
    def listing(offset:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=100),user=Depends(driver),db:Session=Depends(database_session)):
        query=select(Delivery,Message).join(Message,Message.id==Delivery.message_id).where(Delivery.recipient_id==user.id,Delivery.deleted_at.is_(None))
        total=db.scalar(select(func.count()).select_from(query.subquery()))
        rows=db.execute(query.order_by(Message.created_at.desc(),Message.id.desc()).offset(offset).limit(limit)).all()
        return dict(total=total,messages=[view(db,m,d) for d,m in rows])
    @router.get('/api/v1/tf/messages/sent')
    def sent_listing(offset:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=100),user=Depends(driver),db:Session=Depends(database_session)):
        query=select(Message).where(Message.sender_id==user.id)
        total=db.scalar(select(func.count()).select_from(query.subquery()))
        rows=db.scalars(query.order_by(Message.created_at.desc(),Message.id.desc()).offset(offset).limit(limit)).all()
        return dict(total=total,messages=[sent_view(db,m) for m in rows])
    @router.get('/api/v1/tf/messages/sent/{message_id}')
    def sent_detail(message_id:int,user=Depends(driver),db:Session=Depends(database_session)):
        return sent_view(db,sent_owned(db,user,message_id),True)
    @router.get('/api/v1/tf/messages/sent/{message_id}/attachment')
    def sent_attachment(message_id:int,user=Depends(driver),db:Session=Depends(database_session)):
        message=sent_owned(db,user,message_id);file=db.get(Attachment,message.attachment_id) if message.attachment_id else None
        if not file:raise HTTPException(404,_text_source('server_tf_messages.text_bfaa2d8ffe47'))
        from urllib.parse import quote
        return Response(file.content,media_type=file.mime_type,headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(file.filename),'X-Content-Type-Options':'nosniff','Content-Security-Policy':"sandbox; default-src 'none'"})
    @router.post('/api/v1/tf/messages',status_code=201)
    async def send(payload:str=Form(max_length=50000),file:UploadFile|None=File(default=None),user=Depends(driver),db:Session=Depends(database_session)):
        try:data=MessageIn.model_validate_json(payload)
        except ValidationError as exc:raise HTTPException(422,_text_source('server_tf_messages.text_35b72faaf4be')) from exc
        if data.group_id:
            group_owned(db,user,data.group_id)
            data.recipients=list(db.scalars(select(Member.user_id).where(Member.group_id==data.group_id,Member.user_id!=user.id)))
            data.all_tf=False
        selected=targets(db,data);attachment=None
        if file:
            try:content=await file.read(MAX_FILE+1)
            finally:await file.close()
            if not content or len(content)>MAX_FILE:raise HTTPException(413,_text_source('server_tf_messages.text_fc4a9071ea60'))
            filename=PurePosixPath((file.filename or _text_source('server_tf_messages.text_9e313cd30ea1')).replace('\\','/')).name
            if not filename or len(filename)>200 or any(ord(c)<32 or ord(c)==127 for c in filename):raise HTTPException(422,_text_source('server_tf_messages.text_11f2410fea6e'))
            mime='application/octet-stream'
            try:
                with Image.open(io.BytesIO(content)) as image:
                    image.verify()
                    if image.format in ('JPEG','PNG','GIF','WEBP'):mime=Image.MIME[image.format]
            except Exception:pass
            if content.startswith(b'%PDF-'):mime='application/pdf'
            elif len(content)>12 and content[4:8]==b'ftyp':mime='video/mp4'
            elif content.startswith(b'\x1a\x45\xdf\xa3') and b'webm' in content[:4096]:mime='video/webm'
            attachment=Attachment(filename=filename,mime_type=mime,content=content);db.add(attachment);db.flush()
        profile=db.get(TfProfile,user.id)
        message=Message(sender_id=user.id,sender_name=identity(db,user),subject=data.subject,body=data.body,attachment_id=attachment.id if attachment else None);db.add(message);db.flush()
        for target in selected:db.add(Delivery(message_id=message.id,recipient_id=target))
        if data.group_id:db.add(GroupMessage(message_id=message.id,group_id=data.group_id))
        db.commit();return dict(id=message.id,sent=len(selected))
    @router.post('/api/v1/tf/messages/{message_id}/reply',status_code=201)
    async def reply(message_id:int,payload:str=Form(max_length=50000),file:UploadFile|None=File(default=None),user=Depends(driver),db:Session=Depends(database_session)):
        delivery,original=owned(db,user,message_id)
        try:data=MessageIn.model_validate_json(payload)
        except ValidationError as exc:raise HTTPException(422,_text_source('server_tf_messages.text_14ae4d309870')) from exc
        data.recipients=[original.sender_id];data.all_tf=False
        data.group_id=db.scalar(select(GroupMessage.group_id).where(GroupMessage.message_id==original.id))
        return await send(data.model_dump_json(),file,user,db)
    @router.get('/api/v1/tf/messages/{message_id}')
    def detail(message_id:int,user=Depends(driver),db:Session=Depends(database_session)):
        delivery,message=owned(db,user,message_id)
        if delivery.read_at is None:delivery.read_at=now_utc();db.commit()
        return view(db,message,delivery,True)
    @router.put('/api/v1/tf/messages/{message_id}/read')
    def mark(message_id:int,data:ReadIn,user=Depends(driver),db:Session=Depends(database_session)):
        delivery,message=owned(db,user,message_id);delivery.read_at=now_utc() if data.read else None;db.commit();return {'read':data.read}
    @router.delete('/api/v1/tf/messages/{message_id}')
    def remove(message_id:int,user=Depends(driver),db:Session=Depends(database_session)):
        delivery,message=owned(db,user,message_id);delivery.deleted_at=now_utc();db.commit();return {'deleted':True}
    @router.post('/api/v1/tf/messages/{message_id}/forward',status_code=201)
    def forward(message_id:int,data:Recipients,user=Depends(driver),db:Session=Depends(database_session)):
        delivery,original=owned(db,user,message_id);selected=targets(db,data)
        profile=db.get(TfProfile,user.id)
        message=Message(sender_id=user.id,sender_name=identity(db,user),subject=('WG: '+original.subject)[:200],body=original.body,attachment_id=original.attachment_id);db.add(message);db.flush()
        for target in selected:db.add(Delivery(message_id=message.id,recipient_id=target))
        db.commit();return dict(id=message.id,sent=len(selected))
    @router.get('/api/v1/tf/messages/{message_id}/attachment')
    def attachment(message_id:int,user=Depends(driver),db:Session=Depends(database_session)):
        delivery,message=owned(db,user,message_id);file=db.get(Attachment,message.attachment_id) if message.attachment_id else None
        if not file:raise HTTPException(404,_text_source('server_tf_messages.text_bfaa2d8ffe47'))
        from urllib.parse import quote
        return Response(file.content,media_type=file.mime_type,headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(file.filename),'X-Content-Type-Options':'nosniff','Content-Security-Policy':"sandbox; default-src 'none'"})
    return router
