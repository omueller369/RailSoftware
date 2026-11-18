/* Canonical train-event cause. No coordinates, times, revisions or personal free text change. */
(()=>{
 const name='DB-InfraGo',aliases=new Set(),tasks=new Map();let owner=null;
 const named=value=>typeof value==='string'&&['dbinfrago','dbinfraogo'].includes(value.trim().toLowerCase().replace(/[ -]/g,''));
 const canonical=value=>typeof value==='string'&&(named(value)||aliases.has(value))?name:value;
 function normalize(value){
  if(Array.isArray(value)){const items=value.map(normalize);return items.some((item,i)=>item!==value[i])?items:value;}
  if(!value||typeof value!=='object')return value;
  let changed=false;const entries=Object.entries(value).map(([key,item])=>{const next=key==='points'?item:['cause','cause_label'].includes(key)&&typeof item==='string'?canonical(item):normalize(item);changed||=next!==item;return [key,next];});
  const result=Object.fromEntries(entries);if(result.cause===name&&Object.hasOwn(result,'cause_label')&&result.cause_label!==name){result.cause_label=name;changed=true;}
  return changed?result:value;
 }
 function catalogue(rows){
  if(!Array.isArray(rows))return rows;const matches=rows.filter(row=>row.category==='cause'&&(named(row.value)||named(row.label)));
  for(const row of matches){aliases.add(row.value);for(const value of row.aliases||[])aliases.add(value);}
  const target=matches.find(row=>row.value===name)||matches[0];
  return rows.flatMap(row=>matches.includes(row)?row===matches[0]?[{...target,value:name,label:name,active:matches.some(row=>row.active),aliases:[...aliases]}]:[]:[row]);
 }
 async function activate(userId){
  owner=userId;const marker='railsoftware.infra-go.'+userId;
  if(tasks.has(userId))return tasks.get(userId);
  const task=(async()=>{
   try{const cached=JSON.parse(localStorage.getItem('lokzeitleiste.app-defaults')||'null');if(cached)localStorage.setItem('lokzeitleiste.app-defaults',JSON.stringify(catalogue(cached)));}catch{}
   const version='v1:'+[...aliases].sort().join('|');
   try{if(localStorage.getItem(marker)===version)return;
    const prefix='lokzeitleiste.work-report.'+userId;
    for(const key of Object.keys(localStorage)){if(key!==prefix&&!key.startsWith(prefix+'.'))continue;const raw=localStorage.getItem(key);let value;try{value=JSON.parse(raw);}catch{continue;}const changed=normalize(value);if(value!==changed)localStorage.setItem(key,JSON.stringify(changed));}
    await window.GpsRecorder?.normalizeVocabulary?.(userId);
    localStorage.setItem(marker,version);
   }catch{/* Reads and writes also normalize values; retain the retry marker on storage failure. */}
  })();tasks.set(userId,task);try{await task;}finally{tasks.delete(userId);}
 }
 window.InfraGo={name,named,canonical,normalize,catalogue,activate,get owner(){return owner;}};
})();
