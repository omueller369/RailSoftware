/* Die Vorschau liest nur einen lokalen Schnappschuss. Weder Prüfung noch Versand werden ausgelöst. */
(()=>{
const keys={"open": "text_4e1969b1e2d3", "print": "text_62636c6041af", "close": "text_2bb07e2ca209", "draft": "text_2401b34f7275", "notice": "text_362770189a0f", "pdf_hint": "text_5c9f03e3a804", "missing": "text_9f2382bf4c2b", "employee": "text_f050113f7c97", "generated": "text_9e29d6927805", "duty": "text_7ba55aee91f1", "from": "text_d24bb72adf8d", "to": "text_14f6e35c1076", "kind": "text_d688f83e90d4", "pause": "text_0c203d09d682", "allowance": "text_a09ca80f130f", "hotel": "text_0a6249a78d3e", "note": "text_a3d33fa50158", "guests": "text_3200665470e9", "journeys": "text_ceac120bc8a6", "number": "text_f4615d471182", "rotation": "text_47361cd1808b", "start": "text_fbc947dd69c5", "end": "text_eca02cbdde99", "cause": "text_930e9267dfc3", "reason": "text_effa4fd4e36f", "station": "text_a0eb8ded8a2c", "transport": "text_e34d6e82a7e3", "self_payer": "text_bdff707ff3e4", "pending": "text_ca34bce8b078", "none": "text_2a3da7d85a4f", "yes": "text_a80f0ee6918d", "no": "text_c8b0e451a44b", "error": "text_2f06036b35f8", "help": "text_34b891cf105f"},t=k=>{const value=CtlText.source('report_preview.'+keys[k]);return window.I18n?.t(value)||value;};
const value=v=>v===undefined||v===null||String(v).trim()===''?t('missing'):String(v);
function date(v){const raw=String(v||'');const match=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(raw);return match?match[3]+'.'+match[2]+'.'+match[1]+' '+match[4]+':'+match[5]:value(raw);}
function text(snapshot){
 const r=snapshot.report,lines=[t('draft'),t('notice'),''];
 const row=(key,v)=>lines.push(t(key)+': '+value(v)),range=data=>{row('from',date(data.start_at));row('to',date(data.end_at));},place=(code,name)=>[code,name].filter(Boolean).join(' · ');
 row('employee',[snapshot.owner.first_name,snapshot.owner.last_name,snapshot.owner.username].filter(Boolean).join(' '));row('generated',new Date().toLocaleString(window.I18n?.locale||'de-DE',{timeZone:'Europe/Berlin'}));
 lines.push('',t('duty'));row('kind',r.kind);range(r);row('pause',Number.isFinite(snapshot.pause)?snapshot.pause:null);row('allowance',(r.ausbleibe||[]).join(', '));if(r.in_hotel)row('hotel',[r.hotel_name,r.hotel_location].filter(Boolean).join(' · '));if(r.overrun_reason)row('note',r.overrun_reason);
 function guest(data){row('start',place(data.start_station,data.start_station_name));row('end',place(data.end_station,data.end_station_name));range(data);row('transport',[data.transport,data.transport_detail].filter(Boolean).join(' · '));row('self_payer',t(data.self_payer?'yes':'no'));}
 lines.push('',t('guests'));if(!r.trips?.length)lines.push(t('none'));for(const trip of r.trips||[]){guest(trip);lines.push('');}if(snapshot.guest){lines.push(t('pending'));guest(snapshot.guest);}
 const event=data=>{row('cause',[data.cause,data.cause_detail].filter(Boolean).join(' · '));row('reason',[data.reason,data.reason_detail].filter(Boolean).join(' · '));row('station',place(data.station,data.station_name));range(data);};
 lines.push('',t('journeys'));if(!r.train_journeys?.length)lines.push(t('none'));
 for(const [i,train]of (r.train_journeys||[]).entries()){lines.push('',t('number')+' '+(i+1));row('number',train.train_number);row('rotation',train.rotation_name);row('start',place(train.start_station,train.start_station_name));row('end',place(train.end_station,train.end_station_name));range(train);for(const item of train.events||[]){lines.push('');event(item);}const editor=snapshot.editors?.find(e=>e.id===train.id);if(editor?.pending){lines.push('',t('pending'));event(editor.eventFields);}}
 return lines.join('\n');
}
let dialog,previousTitle,opener,printing=false;
function cleanup(){document.body.classList.remove('report-preview-printing');if(previousTitle!==undefined){document.title=previousTitle;previousTitle=undefined;}}
function open(snapshot){
 if(dialog?.open)return;opener=document.activeElement;const title=t('open')+' – '+(snapshot.report.start_at||'').slice(0,10);const content=text(snapshot);
 dialog=document.createElement('dialog');dialog.id='reportPreviewDialog';dialog.setAttribute('aria-labelledby','reportPreviewTitle');
 const head=document.createElement('header'),close=document.createElement('button'),heading=document.createElement('h2'),print=document.createElement('button'),hint=document.createElement('p'),status=document.createElement('p'),article=document.createElement('pre');
 close.type=print.type='button';close.textContent='×';close.setAttribute('aria-label',t('close'));heading.id='reportPreviewTitle';heading.textContent=title;print.textContent=t('print');hint.textContent=t('pdf_hint');status.setAttribute('role','status');article.id='reportPreviewContent';article.textContent=content;article.setAttribute('data-i18n-ignore','');head.append(close,heading,print);dialog.append(head,hint,status,article);document.body.append(dialog);
 const view=dialog,returnFocus=opener;const dismiss=()=>{cleanup();view.close();view.remove();returnFocus?.focus?.({preventScroll:true});};close.onclick=dismiss;view.addEventListener('close',()=>{view.remove();if(dialog===view){cleanup();returnFocus?.focus?.({preventScroll:true});}});view.addEventListener('cancel',e=>{e.preventDefault();dismiss();});
 print.onclick=async()=>{if(printing)return;printing=true;print.disabled=true;status.textContent='';try{if(window.AndroidPortal){if(!window.AndroidPortal.printReport)throw Error(t('error'));await window.AndroidPortal.printReport({title:title.slice(0,200),text:content});}else{previousTitle=document.title;document.title=title;document.body.classList.add('report-preview-printing');window.print();}}catch(error){cleanup();status.textContent=error.message||t('error');}finally{printing=false;print.disabled=false;}};
 dialog.showModal();close.focus();
}
window.addEventListener('afterprint',cleanup);window.ReportPreview={open,text};
})();
