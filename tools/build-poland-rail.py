# Bereitet polnische Referenznetz und die manuelle Streckenerfassung aus den eingecheckten Quellen reproduzierbar auf.
"""Reproducible ODbL-only Poland reference tiles, separate from M1 and qualifications."""
import argparse,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'backend/lokzeitleiste';REF=ROOT/'reference/poland-rail';OUT=ROOT/'static/poland-rail-data';SCALE=10_000_000;GRID=512

def simplify(points,tolerance):
    if len(points)<3:return points
    keep={0,len(points)-1};stack=[(0,len(points)-1)]
    while stack:
        a,b=stack.pop();x,y=points[a];dx=points[b][0]-x;dy=points[b][1]-y;length=dx*dx+dy*dy;best=tolerance*tolerance;at=None
        for i in range(a+1,b):
            px,py=points[i];f=max(0,min(1,((px-x)*dx+(py-y)*dy)/length)) if length else 0;d=(px-x-f*dx)**2+(py-y-f*dy)**2
            if d>best:best=d;at=i
        if at is not None:keep.add(at);stack.extend([(a,at),(at,b)])
    return [points[i] for i in sorted(keep)]
def build(check=False):
    raw=(REF/'poland.json.gz').read_bytes();manifest=json.loads((REF/'manifest.json').read_text());assert hashlib.sha256(raw).hexdigest()==manifest['canonical_sha256'];data=json.loads(gzip.decompress(raw));tiles={};overview=set();step=400 # Etwa ein Kilometer auf polnischer Breite, ausschließlich für die Länderübersicht.
    for ident,name,line in data:
        points=[(round((lon+180)/360*SCALE),round((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*SCALE)) for lon,lat in line]
        detail=simplify(points,8) # Für die Anzeige auf etwa 20 Meter vereinfachen; der ursprüngliche Quellbestand bleibt erhalten.
        box=[min(p[0] for p in detail),min(p[1] for p in detail),max(p[0] for p in detail),max(p[1] for p in detail)];flat=[c for p in detail for c in p];row=[ident,box,flat]
        for x in range(box[0]*GRID//SCALE,box[2]*GRID//SCALE+1):
            for y in range(box[1]*GRID//SCALE,box[3]*GRID//SCALE+1):tiles.setdefault(f'tile-{x}-{y}',[]).append(row)
        coarse=simplify(points,step/2);previous=None
        for px,py in coarse:
            p=(round(px/step)*step,round(py/step)*step)
            if previous is not None and p!=previous:overview.add(tuple(sorted((previous,p))))
            previous=p
    summary=[]
    for a,b in sorted(overview):summary.append([[min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])],[*a,*b]])
    bodies={'overview':dict(schema=1,scale=SCALE,grid=GRID,tiles=sorted(tiles),lines=summary)}
    bodies.update({key:dict(schema=1,scale=SCALE,lines=rows) for key,rows in tiles.items()})
    points_file=ROOT/'reference/poland-stk/map-points.json.gz'
    if points_file.exists():
        point_tiles=json.loads(gzip.decompress(points_file.read_bytes()))
        bodies['overview']['points']=[p for values in point_tiles.values() for p in values if p[2]<2]
        for key,values in point_tiles.items():
            if key not in bodies:bodies[key]=dict(schema=1,scale=SCALE,lines=[]);bodies['overview']['tiles'].append(key)
            bodies[key]['points']=values
        bodies['overview']['tiles'].sort()
    expected={}
    for key,value in bodies.items():
        content=('/* © OpenStreetMap contributors / Geofabrik, ODbL 1.0. Öffentliche polnische Kartenreferenz; Quelle: reference/poland-rail. */\nwindow.PolandRailNetwork.receive('+json.dumps(key)+','+json.dumps(value,separators=(',',':'))+');\n').encode();expected[key+'.js']=hashlib.sha256(content).hexdigest();path=OUT/(key+'.js')
        if check:assert path.read_bytes()==content,path
        else:OUT.mkdir(exist_ok=True);path.write_bytes(content)
    if check:assert manifest['bundles']==expected
    else:
        for p in OUT.glob('*.js'):
            if p.name not in expected:p.unlink()
        manifest.update(bundles=expected,overview_segments=len(summary),detail_tiles=len(tiles),scale=SCALE);(REF/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Poland OSM reference:',len(data),'source parts,',len(summary),'overview segments,',len(tiles),'detail tiles verified')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');build(p.parse_args().check)
