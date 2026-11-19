(()=>{
const button=document.getElementById('refresh'),body=document.getElementById('accessRows'),status=document.getElementById('status');
async function load(){button.disabled=true;status.textContent='';try{
 const response=await fetch('/api/v1/admin/portal-access',{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw Error();
 const rows=await response.json();body.replaceChildren();for(const row of rows){const tr=document.createElement('tr');for(const name of ['tf_number','last_name','first_name','date','time','android_version']){const td=document.createElement('td');td.textContent=row[name]||'–';tr.append(td);}body.append(tr);}
}catch(_){status.textContent=globalThis.CtlText.source('portal_access.text_bd73fd051432');}finally{button.disabled=false;}}
button.addEventListener('click',load);load();
})();
