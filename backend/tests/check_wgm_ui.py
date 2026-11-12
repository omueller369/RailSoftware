"""WGM administration: own fields, safe display, view/edit/create and responsive forms."""
import re
import check_work_report_layout as runner
from localized_fixtures import localize_html


def fixture():
    page=localize_html((runner.STATIC/'wgm.html').read_text())
    page=re.sub(r'<script\b[^>]*>.*?</script>','',page,flags=re.S)
    page=re.sub(r'<link\b[^>]*>','',page)
    css='\n'.join((runner.STATIC/name).read_text() for name in ['tf-portal.css','responsive.css'])
    mocks=r'''
const writes=[],person={id:42,username:'wgm.anna',first_name:'<img src=x onerror=alert(1)>',last_name:'Wagen',personnel_number:'W-001',email:'wgm@example.com',birth_date:'1990-01-01',vacation_days:30,weekly_minutes:2400,entry_date:'2020-01-01',exit_date:null,immediate_block:false,gender:'female',nationality:'DE',addresses:[{street:'Testweg',house_number:'1',postal_code:'01234',city:'Berlin',federal_state:'BE',is_postal:true}]};
window.fetch=async(url,options={})=>{let data;if(options.method){writes.push({url,...options,data:JSON.parse(options.body)});Object.assign(person,JSON.parse(options.body));data=person;}else if(url==='/api/v1/admin/me')data={permissions:{wgm:3}};else if(url.endsWith('/metadata'))data={today:'2026-11-12',countries:{DE:{de:'Deutschland',en:'Germany',pl:'Niemcy'}}};else data=[person];return {ok:true,status:200,json:async()=>data};};
'''
    scripts=(runner.STATIC/'messages.js').read_text()+'\n'+mocks+(runner.STATIC/'wgm.js').read_text()
    checks=r'''
(async()=>{
 const assert=(ok,message)=>{if(!ok)throw Error(message);};
 for(let i=0;i<100&&!document.querySelector('#wgmRows tr');i++)await new Promise(resolve=>setTimeout(resolve,0));
 assert(document.querySelectorAll('#wgmRows tr').length===1,'Separate WGM list');assert(!document.querySelector('#wgmRows img'),'Name remains plain text');
 for(const name of ['tf_number','bahncard','driver_type','home_station','employee_category'])assert(!document.querySelector('[name='+name+']'),'No TF-specific field: '+name);
 assert(document.querySelector('[name=email]').closest('label').textContent.includes('E-Mail des WGM'),'Own email label');
 document.querySelector('#wgmRows button').click();const dialog=document.getElementById('wgmDialog'),form=document.getElementById('wgmForm');
 assert(dialog.open&&form.elements.first_name.disabled,'Read-only view');assert(document.getElementById('wgmSave').hidden,'Read-only has no save');document.getElementById('wgmClose').click();
 document.querySelectorAll('#wgmRows button')[1].click();assert(!form.elements.first_name.disabled,'Editable view');assert(form.elements.personnel_number.value==='W-001','Correct employee');
 form.elements.last_name.value='Geändert';form.elements.weekly_hours.value='35';await form.onsubmit({preventDefault(){}});
 assert(writes.length===1&&writes[0].method==='PUT'&&writes[0].url.endsWith('/42'),'Edit writes own WGM endpoint');assert(writes[0].data.weekly_minutes===2100&&writes[0].data.addresses[0].postal_code==='01234','Contract hours and addresses preserved');
 for(const key of ['tf_number','bahncard','driver_type','home_station','password'])assert(!(key in writes[0].data),'No TF fields or password in update');
 document.getElementById('wgmNew').click();assert(dialog.open&&!form.elements.password.disabled,'Separate create form with initial password');
 assert(form.elements.username.getAttribute('pattern').includes('a-z'),'Generic username, no TF number pattern');
 for(const field of form.querySelectorAll('.wgm-grid input,.wgm-grid select')){const rect=field.getBoundingClientRect();assert(rect.left>=0&&rect.right<=innerWidth+1,'Form fields fit viewport');}
 document.getElementById('wgmClose').click();assert(document.documentElement.scrollWidth<=innerWidth+1,'Page fits viewport');
 window.parent.postMessage({layoutStatus:'pass'},'*');
})().catch(error=>window.parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return page.replace('</head>','<style>'+css+'</style></head>').replace('</body>','<script>'+scripts+checks+'</script></body>')


if __name__=='__main__':
    runner.fixture=fixture
    runner.main()
