# Echte Browserabläufe für Gruppen, Ungelesenzähler und Medienanhänge.
import argparse
from check_coordination_ui import base
from check_work_report_layout import STATIC
from browser_realtime import check_pages

def fixture():
    setup=r'''
localStorage.clear();window.I18n={t:s=>s,locale:'de-DE'};
let directUnread=150,groupUnread=120,created=null,sent=null,postedFile=null;
const members=[{id:7,name:'Eigenes Konto',group:'TF'},{id:8,name:'Bestehender Kontakt',group:'TF'},{id:10,name:'Neuer Kontakt',group:'TF'}];
const groupMessages=[{id:91,created_at:'2026-11-26T08:00:00Z',body:'Bild',sender_name:'Anderer TF',mine:false,read:true,attachment:{filename:'bild.png',mime_type:'image/png',url:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='}},{id:92,created_at:'2026-11-26T08:01:00Z',body:'Video',sender_name:'Anderer TF',mine:false,read:true,attachment:{filename:'video.webm',mime_type:'video/webm',url:'data:video/webm;base64,'}}];
window.fetch=async(url,options={})=>{const path=String(url).split('?')[0];let data={};if(path.endsWith('/account/me'))data={id:7,role:'tf'};
else if(path.endsWith('/recipients'))data=members;
else if(path.endsWith('/chats'))data=[{peer_id:8,name:members[1].name,count:2,unread:directUnread,last_at:'2026-11-26T08:00:00Z'}];
else if(path.endsWith('/groups')&&options.method==='POST'){created=JSON.parse(options.body);data={id:8,name:created.name,kind:'group',unread:0};}
else if(path.endsWith('/groups'))data=[{id:9,name:'Vorhandene Gruppe',kind:'group',unread:groupUnread,count:15,last_at:'2026-11-26T08:30:00Z'},...(created?[{id:8,name:created.name,kind:'group',unread:0,count:2,last_at:'2026-11-26T08:40:00Z'}]:[])];
else if(path.includes('/groups/')){groupUnread=0;data={messages:groupMessages,more:false};}
else if(path.includes('/chats/8')){directUnread=0;data={messages:[{id:11,created_at:'2026-11-26T08:00:00Z',body:'Privater Text',mine:false,read:true}],more:false};}
else if(path.endsWith('/messages')&&options.method==='POST'){sent=JSON.parse(options.body.get('payload'));postedFile=options.body.get('file');data={id:100};}
return new Response(JSON.stringify(data));};
'''
    checks=r'''
await until(()=>document.querySelector('[data-chat-key="direct:8"]'));
const contact=()=>document.querySelector('[data-chat-key="direct:8"]'),group=()=>document.querySelector('[data-chat-key="group:9"]');
assert(contact().classList.contains('has-chat'),'An existing direct chat has its own color');assert(!document.querySelector('[data-chat-key="direct:10"]').classList.contains('has-chat'),'Unused contacts keep the default color');
assert(contact().querySelector('.chat-unread').textContent==='99'&&group().querySelector('.chat-unread').textContent==='99','Contact and group badges are capped at 99');
const box=contact().getBoundingClientRect(),badge=contact().querySelector('.chat-unread').getBoundingClientRect();assert(badge.right<=box.right&&badge.top>=box.top&&badge.left>box.left,'Badge stays in the upper right of its contact');
contact().click();await until(()=>document.querySelector('.chat-bubble'));await until(()=>!contact().querySelector('.chat-unread'));assert(contact().classList.contains('selected'),'Opened chat is selected');
document.getElementById('chatBody').value='Privater Entwurf';document.getElementById('chatBody').dispatchEvent(new Event('input'));
document.getElementById('chatCreateGroup').click();assert(document.getElementById('chatGroupDialog').open,'Group creation opens a dialog');
document.getElementById('chatGroupName').value='  ';document.getElementById('chatGroupForm').dispatchEvent(new Event('submit',{cancelable:true}));assert(!created&&document.getElementById('chatGroupStatus').textContent,'Empty group is rejected');
document.getElementById('chatGroupName').value='Einsatzgruppe';document.querySelector('#chatGroupMembers input[value="8"]').checked=true;document.getElementById('chatGroupForm').dispatchEvent(new Event('submit',{cancelable:true}));
await until(()=>document.getElementById('chatTitle').textContent==='Einsatzgruppe'&&document.querySelector('video'));
assert(created.name==='Einsatzgruppe'&&created.members.join(',')==='8','Chosen group name and members are submitted explicitly');assert(!document.getElementById('chatGroupDialog').open,'Dialog closes after creation');
assert(document.getElementById('chatBody').value===''&&localStorage.getItem('rail.chat.draft.7.8')==='Privater Entwurf','Group and private drafts remain separate even with the same numeric id');
const video=document.querySelector('video');assert(video.controls&&video.playsInline&&!video.autoplay,'Video has inline playback controls and never autoplays');assert(document.querySelector('.chat-bubble img'),'Image is shown inline');assert(document.querySelectorAll('.chat-bubble a[download]').length===2,'Both media attachments have download links');assert(document.querySelector('.chat-bubble strong').textContent==='Anderer TF','Group messages identify the sender');
document.getElementById('chatSearch').value='Video';document.getElementById('chatSearch').dispatchEvent(new Event('input'));await new Promise(r=>setTimeout(r,400));assert(document.querySelector('video')===video,'Refreshing messages preserves the video element');
document.getElementById('chatBody').value='Gruppentext';document.getElementById('chatCompose').dispatchEvent(new Event('submit',{cancelable:true}));await until(()=>sent&&!document.getElementById('chatSend').disabled);assert(sent.group_id===8&&sent.recipients.length===0,'Group message targets its group, never a guessed recipient list');
sent=null;const transfer=new DataTransfer();transfer.items.add(new File(['video fixture'],'clip.mp4',{type:'video/mp4'}));document.getElementById('chatFile').files=transfer.files;assert(document.getElementById('chatCompose').checkValidity(),'An attachment may be sent without a caption');document.getElementById('chatCompose').dispatchEvent(new Event('submit',{cancelable:true}));await until(()=>sent&&!document.getElementById('chatSend').disabled);assert(sent.body==='clip.mp4'&&postedFile.name==='clip.mp4','Attachment-only messages retain a useful filename');
assert(document.documentElement.scrollWidth<=window.innerWidth+2,'Chat fits the screen');
'''
    return base('tf-messages.html',setup,checks,['tf-chat.js'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);args=parser.parse_args()
    assets={'/tf/'+n:STATIC/n for n in ['messages.js','tf-chat.js']}
    check_pages(fixture,args.output_dir,widths=(1280,800,375,320),assets=assets,label='Chat groups and media',timeout=35)
