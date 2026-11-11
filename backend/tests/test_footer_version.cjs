const fs=require('node:fs'),vm=require('./localized-vm.cjs'),assert=require('node:assert/strict');
const source=fs.readFileSync('backend/lokzeitleiste/static/tf-shell.js','utf8');
class E{constructor(tag){this.tag=tag;this.children=[];}append(...items){this.children.push(...items);}prepend(item){this.children.unshift(item);}setAttribute(){}replaceWith(item){this.replacement=item;}}
async function footer(appVersion){
 const oldHeader=new E('header'),oldFooter=new E('footer'),events={};
 const window={addEventListener:(name,fn)=>events[name]=fn};
 if(appVersion!==null)window.AndroidPortal={version:Promise.resolve(appVersion)};
 const document={head:new E('head'),body:new E('body'),createElement:tag=>new E(tag),querySelector:selector=>selector==='header'?oldHeader:oldFooter};
 vm.runInNewContext(source,{window,document,location:{pathname:'/tf'},Intl,Date,setInterval:()=>1,clearInterval(){},fetch:async path=>({ok:true,json:async()=>path.endsWith('/unread')?{count:0}:{first_name:'Test',last_name:'TF',tf_number:'787000',software:'Rail Software',version:'0.26.10',copyright_holder:'IO-Software-Görlitz',copyright_year:2026}})});
 await window.AppShellReady;const text=oldFooter.replacement.children[0].textContent;events.languagechange();assert.equal(oldFooter.replacement.children[0].textContent,text);return text;
}
(async()=>{
 assert.equal(await footer(null),'Rail Software · Version 0.26.10 · Copyright 2026 IO-Software-Görlitz');
 assert.equal(await footer('0.26.42-test.9'),'Rail Software · Version 0.26.42-test.9 · Copyright 2026 IO-Software-Görlitz');
 assert.equal(await footer(undefined),'Rail Software · Version 0.26.10 · Copyright 2026 IO-Software-Görlitz');
 console.log('Footer: server version on web, installed APK version on Android, copyright and language refresh: PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
