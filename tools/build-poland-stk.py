"""Build public, separate ODbL Poland STK offline bundles from the prepared graph."""
import argparse,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'backend/lokzeitleiste';REF=ROOT/'reference/poland-stk';OUT=ROOT/'static/poland-stk-data'
KINDS={'railway_station':0,'railway_halt':1,'junction':2,'endpoint':3}
def packed(value):return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
def build(check=False):
    raw=(REF/'graph.json.gz').read_bytes();manifest=json.loads((REF/'manifest.json').read_text());assert hashlib.sha256(raw).hexdigest()==manifest['graph_sha256'];graph=json.loads(gzip.decompress(raw));revision=manifest['graph_sha256'];scale=graph['scale'];named=[];junctions=[];point_tiles={}
    for p in graph['points']:
        if p['kind'].startswith('railway_'):named.append([p['id'],p['name'],KINDS[p['kind']],round(p['lon']*scale),round(p['lat']*scale),p['node'],round(p['distance_m']*10),bool(p.get('junction'))])
        else:junctions.append([p['id'],KINDS[p['kind']],p['node']])
        x=(p['lon']+180)/360;y=(1-math.asinh(math.tan(math.radians(p['lat'])))/math.pi)/2;key=f'tile-{math.floor(x*512)}-{math.floor(y*512)}';point_tiles.setdefault(key,[]).append([p['id'],p['name'],KINDS[p['kind']],round(x*10_000_000),round(y*10_000_000),p['node'] is not None,round(p['distance_m']*10),bool(p.get('junction'))])
    topology=dict(schema=1,revision=revision,scale=scale,nodes=graph['nodes'],edges=[[e[0],e[1],e[2]] for e in graph['edges']],stations=named,junctions=junctions,counts=manifest['counts']);files={'topology.json':packed(topology)}
    for i in range(0,len(graph['edges']),256):files[f'geometry-{i//256}.json']=packed(dict(schema=1,revision=revision,offset=i,edges=[e[3] for e in graph['edges'][i:i+256]]))
    files['manifest.json']=packed(dict(schema=1,revision=revision,counts=manifest['counts'],snapshot=manifest['snapshot'],node_count=len(graph['nodes']),edge_count=len(graph['edges'])))
    # Canonical source for point rendering in the existing tiled rail layer.
    points_raw=gzip.compress(packed(point_tiles),mtime=0);points_path=REF/'map-points.json.gz'
    if check:assert points_path.read_bytes()==points_raw
    else:points_path.write_bytes(points_raw)
    hashes={}
    for name,data in files.items():
        hashes[name]=hashlib.sha256(data).hexdigest();path=OUT/name
        if check:assert path.read_bytes()==data,path
        else:OUT.mkdir(exist_ok=True);path.write_bytes(data)
    if check:assert manifest['bundles']==hashes
    else:
        for p in OUT.glob('*.json'):
            if p.name not in hashes:p.unlink()
        manifest['bundles']=hashes;(REF/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Poland STK:',len(named),'station/halts,',len(junctions),'derived nodes,',len(files),'offline bundles verified')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');build(p.parse_args().check)
