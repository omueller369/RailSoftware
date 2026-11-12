const fs=require('node:fs'),vm=require('./localized-vm.cjs'),assert=require('node:assert/strict');
class E{constructor(){this.attrs={};this.children=[];this.events={};this.hidden=false;this.value='';}setAttribute(k,v){this.attrs[k]=v;}addEventListener(k,fn){this.events[k]=fn;}contains(node){return this===node||this.children.includes(node);}focus(){focused=this;}}
let focused;const ids={workReport:new E(),reportDetails:new E()};for(const name of ['duty','train','month']){ids['reportTab-'+name]=new E();ids['reportPanel-'+name]=new E();}
const field=new E();field.value='2026-11-12T23:45';ids['reportPanel-duty'].children.push(field);ids.reportDetails.hidden=true;
const window={},context={window,document:{getElementById:id=>ids[id]}};vm.runInNewContext(fs.readFileSync('backend/lokzeitleiste/static/report-tabs.js','utf8'),context);
const tabs=window.ReportTabs;assert.equal(tabs.active,'duty');assert(ids.reportDetails.hidden,'Initialization does not expose incomplete report');
let changes=[];tabs.onchange=name=>changes.push(name);tabs.activate('train');assert(!ids.reportDetails.hidden);assert(ids['reportPanel-duty'].hidden);assert(!ids['reportPanel-train'].hidden);tabs.activate('month');assert(ids.reportDetails.hidden);assert(!ids['reportPanel-month'].hidden);assert.equal(field.value,'2026-11-12T23:45');
ids.workReport.events.invalid({target:field});assert.equal(tabs.active,'duty');assert(!ids.reportDetails.hidden);
const press=(name,key)=>ids['reportTab-'+name].onkeydown({key,preventDefault(){}});
press('duty','ArrowLeft');assert.equal(tabs.active,'month');assert.strictEqual(focused,ids['reportTab-month']);press('month','Home');assert.equal(tabs.active,'duty');press('duty','End');assert.equal(tabs.active,'month');assert.equal(ids['reportTab-month'].attrs['aria-selected'],'true');assert.equal(ids['reportTab-duty'].tabIndex,-1);
// Existing report open/restore paths select duty, while live GPS recovery selects train.
const reportSource=fs.readFileSync('backend/lokzeitleiste/static/work-report.js','utf8').split('// Keep collapse buttons')[0].replace(/\}\)\(\);\s*$/,`window.testTabs={reportFields,setEditor:value=>trainEditor=value};})();`);
vm.runInNewContext(reportSource,{window,document:{getElementById:id=>ids[id]},Intl,Date});let journey;window.testTabs.setEditor({activate:id=>journey=id});window.openActiveGpsReport('active-journey');assert.equal(tabs.active,'train');assert.equal(journey,'active-journey');window.testTabs.reportFields(true);assert.equal(tabs.active,'duty');window.testTabs.reportFields(false);assert.equal(tabs.active,'month');assert.equal(field.value,'2026-11-12T23:45');
console.log('Work report tabs: three preserved panels, keyboard/focus, invalid-field reveal and GPS/duty/month restoration: PASS');
