/* Tabs only change visibility. Editors, drafts and GPS services keep their identity. */
(()=>{
 const names=['duty','train','month'],root=document.getElementById('workReport'),details=document.getElementById('reportDetails');
 const tabs=names.map(name=>document.getElementById('reportTab-'+name)),panels=names.map(name=>document.getElementById('reportPanel-'+name));
 if(!root||!details||tabs.some(tab=>!tab)||panels.some(panel=>!panel))return;
 let active='duty';
 const api=window.ReportTabs={get active(){return active;},onchange:null,activate(name,focus=false,reveal=true){
  if(!names.includes(name))return;
  active=name;
  for(let i=0;i<names.length;i++){const selected=names[i]===name;tabs[i].setAttribute('aria-selected',String(selected));tabs[i].tabIndex=selected?0:-1;panels[i].hidden=!selected;}
  if(reveal)details.hidden=name==='month';
  if(focus)tabs[names.indexOf(name)].focus();
  const notify=()=>{if(active===name)api.onchange?.(name);};
  if(window.requestAnimationFrame)window.requestAnimationFrame(notify);else notify();
 }};
 tabs.forEach((tab,index)=>{
  tab.onclick=()=>api.activate(names[index]);
  tab.onkeydown=event=>{let next;if(event.key==='ArrowRight')next=(index+1)%names.length;else if(event.key==='ArrowLeft')next=(index+names.length-1)%names.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=names.length-1;else return;event.preventDefault();api.activate(names[next],true);};
 });
 root.addEventListener('invalid',event=>{const index=panels.findIndex(panel=>panel.contains(event.target));if(index>=0)api.activate(names[index]);},true);
 api.activate(active,false,false);
})();
