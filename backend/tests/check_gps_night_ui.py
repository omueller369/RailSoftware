# Nachtpalette und eigene Positionssymbole wechseln ohne Neuzeichnen oder veränderte Fahrspurfarben.
import argparse
from browser_realtime import check_pages
from check_work_report_layout import STATIC

def fixture():
    setup="""window.I18n={t:s=>s};window.fetch=()=>{throw Error('No network required');};window.M1BasemapSeed={features:[{properties:{code:'DEU'},geometry:{type:'Polygon',coordinates:[[[10,50],[14,50],[14,54],[10,54],[10,50]]]}}]};window.M1BasemapPlaces=[[1,'Berlin',52,13,1000000]];"""
    checks=r'''
(async()=>{const assert=(v,m)=>{if(!v)throw Error(m);},svg=document.querySelector('svg'),make=tag=>document.createElementNS(svg.namespaceURI,tag),p={x:(13+180)/360,y:(1-Math.asinh(Math.tan(52*Math.PI/180))/Math.PI)/2},size=256*2**8;
M1Map.background(svg,make,{width:600,height:300,size,left:p.x*size-300,top:p.y*size-150,zoom:8});
const path=make('path');path.setAttribute('data-gps-trail','');path.setAttribute('stroke','#436eee');svg.append(path);
const gap=make('path');gap.setAttribute('data-gps-gap','true');gap.setAttribute('stroke','#f6b6d2');svg.append(gap);
GpsPreferences.marker(svg,make,300,150,{marker:'electric',train_number:'12345',speed:10},true);GpsPreferences.marker(svg,make,50,150,{id:9,marker:'diesel'},false);
const icon=svg.querySelector('[data-gps-position] image');assert(icon.getAttribute('width')==='36'&&icon.getAttribute('x')==='-18','Own icon is 50 percent larger and remains centered');assert(svg.querySelector('[data-gps-peer] image').getAttribute('width')==='24','Other shared positions keep their size');
for(const mode of ['light','dark','light']){document.documentElement.dataset.theme=mode;const country=svg.querySelector('[data-m1-country]'),water=svg.querySelector('[data-m1-background]'),label=svg.querySelector('[data-offline-place]');
assert(getComputedStyle(country).fill===(mode==='dark'?'rgb(32, 52, 68)':'rgb(247, 246, 241)'),'Country follows selected mode without rebuilding SVG');assert(getComputedStyle(water).fill===(mode==='dark'?'rgb(16, 28, 40)':'rgb(231, 238, 240)'),'Map background follows selected mode');assert(getComputedStyle(label).fill===(mode==='dark'?'rgb(210, 222, 232)':'rgb(80, 86, 79)'),'Place names remain readable');assert(getComputedStyle(path).stroke==='rgb(67, 110, 238)'&&getComputedStyle(gap).stroke==='rgb(246, 182, 210)','Tracking and signal-gap colors remain unchanged');assert(getComputedStyle(icon).filter==='none','Icon retains original colors');}
const circle=make('svg');GpsPreferences.marker(circle,make,0,0,{marker:'circle'},true);assert(circle.querySelector('circle').getAttribute('r')==='7.5','Circle marker also grows by 50 percent');
parent.postMessage({layoutStatus:'pass'},'*');})().catch(error=>parent.postMessage({layoutStatus:'fail',message:error.stack},'*'));
'''
    return '<!doctype html><html><head><meta charset="utf-8"><style>'+(STATIC/'portal-theme.css').read_text()+'</style></head><body><div class="gps-map"><svg viewBox="0 0 600 300"></svg></div><script>'+setup+'\n'+'\n'.join((STATIC/n).read_text() for n in ['messages.js','gps-settings.js','m1-map.js'])+'\n'+checks+'</script></body></html>'
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);a=p.parse_args();check_pages(fixture,a.output_dir,widths=(800,320),label='GPS night mode and own icon')
