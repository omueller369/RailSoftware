/* Public offline reference geometry. It never adds to a TF's travelled routes. */
(()=>{
const REVISION='46c6219268ba0fb31521540ef19506f6467025ee7663e7bd95909a94771c500a';
let loading;
function seed(){const data=window.RailNetworkSeed;if(data?.schema!==2||data.scale!==100000000||!Array.isArray(data.lines)||!Array.isArray(data.routes))throw Error('Invalid rail network bundle');return data;}
function load(){if(window.RailNetworkSeed)return Promise.resolve(seed());if(loading)return loading;loading=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='/tf/rail-network-data.js?v='+REVISION;script.onload=()=>{try{resolve(seed());}catch(error){reject(error);}};script.onerror=()=>{script.remove();reject(Error('Rail network unavailable'));};document.head.append(script);}).catch(error=>{loading=null;throw error;});return loading;}
function paths(data,view){
 const paths=['','',''];let visible=0;const factor=view.size/data.scale,left=view.left,top=view.top,lowX=(left-8)/factor,lowY=(top-8)/factor,highX=(left+600+8)/factor,highY=(top+650+8)/factor;
 for(const row of data.lines){const bounds=row[2];if(bounds[2]<lowX||bounds[0]>highX||bounds[3]<lowY||bounds[1]>highY)continue;
  const coords=row[view.zoom<=9?4:3];let path='';for(let i=0;i<coords.length;i+=2)path+=(i?'L':'M')+(coords[i]*factor-left).toFixed(1)+' '+(coords[i+1]*factor-top).toFixed(1);paths[row[1]]+=path;visible++;
 }
 return {paths,visible};
}
function draw(svg,make,data,view){const result=paths(data,view);for(const [state,d] of result.paths.entries()){if(!d)continue;const path=make('path');path.setAttribute('d',d);path.setAttribute('fill','none');path.setAttribute('stroke','#000000');path.setAttribute('stroke-width',state===0?'2.7':'3.2');path.setAttribute('stroke-linecap','round');path.setAttribute('stroke-linejoin','round');if(state)path.setAttribute('stroke-dasharray',state===1?'10 6':'4 6');path.setAttribute('data-rail-network',String(state));path.setAttribute('aria-hidden','true');svg.append(path);}return result.visible;}
window.RailNetwork={load,paths,draw,revision:REVISION};
})();
