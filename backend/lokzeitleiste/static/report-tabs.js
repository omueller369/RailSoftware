/* Gemeinsame Verarbeitung für Berichte und die zugehörigen Prüf- und Versandabläufe. */
/* Reiter ändern nur die Sichtbarkeit. Bearbeitung, Entwürfe und GPS-Dienste bleiben bestehen. */
(()=>{
 const names=['month','duty','train'],root=document.getElementById('workReport'),details=document.getElementById('reportDetails');
 const tabs=names.map(name=>document.getElementById('reportTab-'+name)),panels=names.map(name=>document.getElementById('reportPanel-'+name));
 if(!root||!details||tabs.some(tab=>!tab)||panels.some(panel=>!panel))return;
 let active='month',opened=false;
 const api=window.ReportTabs={get active(){return active;},get opened(){return opened;},setOpen(value){opened=!!value;tabs[2].hidden=!opened;document.getElementById('dutyFields').hidden=!opened;if(!opened)api.activate('month');},onchange:null,activate(name,focus=false,reveal=true){
  if(!names.includes(name)||!opened&&name==='train')return;
  active=name;
  for(let i=0;i<names.length;i++){const selected=names[i]===name;tabs[i].setAttribute('aria-selected',String(selected));tabs[i].tabIndex=selected?0:-1;panels[i].hidden=!selected;}
  if(reveal)details.hidden=!opened||name==='month';
  if(focus)tabs[names.indexOf(name)].focus();
  const notify=()=>{if(active===name)api.onchange?.(name);};
  if(window.requestAnimationFrame)window.requestAnimationFrame(notify);else notify();
 }};
 tabs.forEach((tab,index)=>{
  tab.onclick=()=>api.activate(names[index]);
  tab.onkeydown=event=>{const available=names.filter(n=>n!=='train'||opened);let next;if(event.key==='ArrowRight')next=(available.indexOf(names[index])+1)%available.length;else if(event.key==='ArrowLeft')next=(available.indexOf(names[index])+available.length-1)%available.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=available.length-1;else return;event.preventDefault();api.activate(available[next],true);};
 });
 for(const type of ['invalid','ctlrevealfield'])root.addEventListener(type,event=>{const index=panels.findIndex(panel=>panel.contains(event.target));if(index>=0)api.activate(names[index]);},true);
 api.setOpen(false);
 api.activate(active,false,false);
})();
