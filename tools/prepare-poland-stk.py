# Bereitet polnische Referenznetz und die manuelle Streckenerfassung aus den eingecheckten Quellen reproduzierbar auf.
"""Prepare the separate OSM Poland STK graph. Build-time only: shapely>=2 required.
Input: the 16 matching Geofabrik transport point exports and railway metadata.
The original rail geometry remains in reference/poland-rail/poland.json.gz.
"""
import argparse,collections,gzip,hashlib,json,math
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
ROOT=Path(__file__).resolve().parents[1]/'backend/lokzeitleiste';REF=ROOT/'reference/poland-stk';S=10_000_000

def packed(x):return json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()
def edgekey(a,b):return (min(a,b)<<32)|max(a,b)
def mercator(lon,lat):return(lon*111319.49079327358,math.asinh(math.tan(math.radians(lat)))*6378137)
def inverse(x,y):return(x/111319.49079327358,math.degrees(math.atan(math.sinh(y/6378137))))
def metres(a,b):
    lon1,lat1=a[:2];lon2,lat2=b[:2];p,q=math.radians(lat1/S),math.radians(lat2/S);d=math.sin((q-p)/2)**2+math.cos(p)*math.cos(q)*math.sin(math.radians((lon2-lon1)/S)/2)**2
    return 12742000*math.asin(min(1,math.sqrt(d)))
def simplify(points,tolerance=500):
    if len(points)<3:return points
    keep={0,len(points)-1};stack=[(0,len(points)-1)]
    while stack:
        a,b=stack.pop();x,y=points[a];dx,dy=points[b][0]-x,points[b][1]-y;length=dx*dx+dy*dy;best=tolerance*tolerance;at=None
        for i in range(a+1,b):
            px,py=points[i];f=max(0,min(1,((px-x)*dx+(py-y)*dy)/length)) if length else 0;distance=(px-x-f*dx)**2+(py-y-f*dy)**2
            if distance>best:best=distance;at=i
        if at is not None:keep.add(at);stack.extend([(a,at),(at,b)])
    return [points[i] for i in sorted(keep)]
def main(source):
    source=json.loads(Path(source).read_text());assert len(source['sources'])==16
    rail_raw=(ROOT/'reference/poland-rail/poland.json.gz').read_bytes();rails=json.loads(gzip.decompress(rail_raw));nodes=[];bycoord={};adj=[];way_by_edge={};ways=[];levels=[];way_nodes=[]
    def node(key):
        if key not in bycoord:bycoord[key]=len(nodes);nodes.append(key);adj.append(set())
        return bycoord[key]
    def connect(a,b,way):
        if a==b:return
        adj[a].add(b);adj[b].add(a);way_by_edge.setdefault(edgekey(a,b),way)
    for ident,name,line in rails:
        layer=int(source['rails'].get(ident,{}).get('layer') or 0);indexes=[];projected=[]
        for lon,lat in line:
            indexes.append(node((round(lon*S),round(lat*S),layer)));projected.append(mercator(lon,lat))
        for a,b in zip(indexes,indexes[1:]):connect(a,b,int(ident))
        ways.append(LineString(projected));levels.append(layer);way_nodes.append(indexes)
    print('Raw graph',len(nodes),'nodes',len(way_by_edge),'edges',flush=True)
    # Höhenwechsel nur bei einem unverzweigten Paar offener Endpunkte verbinden.
    dangling=collections.defaultdict(list)
    for i,links in enumerate(adj):
        if len(links)==1:dangling[nodes[i][:2]].append(i)
    transitions=0
    for values in dangling.values():
        if len(values)==2 and nodes[values[0]][2]!=nodes[values[1]][2]:connect(*values,0);transitions+=1
    tree=STRtree(ways);splits=collections.defaultdict(list);points=[];anchor_nodes=set();length_cache={}
    for raw in source['points']:
        p=dict(raw);shape=Point(mercator(p['lon'],p['lat']));indexes,distances=tree.query_nearest(shape,all_matches=True,return_distance=True);distance=float(min(distances))*math.cos(math.radians(p['lat']));p['distance_m']=round(distance,1);p['node']=None
        same_layers={levels[int(i)] for i,d in zip(indexes,distances) if abs(float(d)-min(distances))<.01}
        if distance>200:p['match']='outside_corridor'
        elif len(same_layers)!=1:p['match']='ambiguous_grade'
        else:
            index=min(map(int,indexes),key=lambda i:int(rails[i][0]));line=ways[index];at=line.project(shape);projected=list(line.coords)
            if index not in length_cache:
                lengths=[0.0]
                for a,b in zip(projected,projected[1:]):lengths.append(lengths[-1]+math.dist(a,b))
                length_cache[index]=lengths
            import bisect
            lengths=length_cache[index];segment=max(0,min(len(projected)-2,bisect.bisect_right(lengths,at)-1));a,b=way_nodes[index][segment:segment+2];width=lengths[segment+1]-lengths[segment];fraction=max(0,min(1,(at-lengths[segment])/width)) if width else 0
            if at-lengths[segment]<.5:anchor=a
            elif lengths[segment+1]-at<.5:anchor=b
            else:
                snap=line.interpolate(at);lon,lat=inverse(snap.x,snap.y);anchor=node((round(lon*S),round(lat*S),levels[index]));splits[edgekey(a,b)].append((fraction if a<b else 1-fraction,anchor))
            p['node']=anchor;p['match']='linked';anchor_nodes.add(anchor)
        points.append(p)
    for key,insertions in splits.items():
        a,b=key>>32,key&0xffffffff
        if b not in adj[a]:continue
        way=way_by_edge.pop(key);adj[a].discard(b);adj[b].discard(a);chain=[a]+[n for _,n in sorted(set(insertions))]+[b]
        for c,d in zip(chain,chain[1:]):connect(c,d,way)
    kept={i for i,links in enumerate(adj) if len(links)!=2}|anchor_nodes;visited=set();chains=[]
    def walk(start,end):
        route=[start];ids=set();a,b=start,end
        while True:
            key=edgekey(a,b)
            if key in visited:break
            visited.add(key);way=way_by_edge.get(key)
            if way:ids.add(way)
            route.append(b)
            if b in kept:break
            choices=adj[b]-{a}
            if not choices:break
            a,b=b,next(iter(choices))
        return route,sorted(ids)
    for a in sorted(kept,key=lambda i:nodes[i]):
        for b in sorted(adj[a],key=lambda i:nodes[i]):
            if edgekey(a,b) in visited:continue
            route,ids=walk(a,b)
            if len(route)>1:chains.append((route,ids))
    print('Compressed graph',len(kept),'nodes',len(chains),'edges',flush=True)
    indexes={old:i for i,old in enumerate(sorted(kept,key=lambda i:nodes[i]))};compact_nodes=[list(nodes[i]) for i in sorted(kept,key=lambda i:nodes[i])];edges=[]
    for route,ids in chains:
        coords=[];length=0
        for i,n in enumerate(route):
            if i:length+=metres(nodes[route[i-1]],nodes[n])
            point=nodes[n][:2]
            if not coords or coords[-1]!=point:coords.append(point)
        if len(coords)<2 or length<.1:continue
        flat=[c for p in simplify(coords) for c in p];edges.append([indexes[route[0]],indexes[route[-1]],round(length,2),flat,ids])
    for p in points:
        if p['node'] is not None:
            old=p['node'];p['junction']=len(adj[old])>2;p['node']=indexes[old]
    named_nodes={p['node'] for p in points if p['node'] is not None}
    for old,i in indexes.items():
        if i in named_nodes:continue
        lon,lat,layer=nodes[old];ident='PL:J'+hashlib.sha256(packed(nodes[old])).hexdigest()[:12];points.append(dict(id=ident,osm_id=None,name='',kind='junction' if len(adj[old])>2 else 'endpoint',lon=lon/S,lat=lat/S,node=i,junction=len(adj[old])>2,distance_m=0,match='linked'))
    graph=dict(schema=1,scale=S,nodes=compact_nodes,edges=edges,points=points);REF.mkdir(exist_ok=True);raw=gzip.compress(packed(graph),mtime=0);(REF/'graph.json.gz').write_bytes(raw);source_bytes=gzip.compress(packed(source),mtime=0);(REF/'source.json.gz').write_bytes(source_bytes)
    counts=dict(stations=sum(p['kind']=='railway_station' for p in points),halts=sum(p['kind']=='railway_halt' for p in points),junctions=sum(p['kind']=='junction' for p in points),endpoints=sum(p['kind']=='endpoint' for p in points),unlinked=sum(p['node'] is None for p in points))
    manifest=dict(schema=1,source='OpenStreetMap / Geofabrik',licence='ODbL 1.0',licence_url='https://opendatacommons.org/licenses/odbl/1-0/',snapshot='2026-11-19',prepared_on='2026-11-23',source_sha256=hashlib.sha256(source_bytes).hexdigest(),rail_source_sha256=hashlib.sha256(rail_raw).hexdigest(),graph_sha256=hashlib.sha256(raw).hexdigest(),counts=counts,nodes=len(compact_nodes),edges=len(edges),grade_transitions=transitions,sources=source['sources'],method='Coordinates plus layer; only unbranched dangling endpoint pairs join different levels. Station projection max 200 m; equal-distance different-level candidates remain unlinked. Junctions/endpoints are derived OSM reference nodes, not official operating-point identities.')
    (REF/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(counts,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);main(p.parse_args().source)
