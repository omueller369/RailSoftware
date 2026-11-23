# Gemeinsame Verarbeitung für Streckenkenntnisse und Referenzgeometrie.
"""Geometry check for an explicit selection of parallel M1 sections (200 m corridor)."""
import gzip,json,math
from functools import lru_cache
from .route_knowledge_mapping import REF

@lru_cache(maxsize=1)
def lines():
    result={}
    for row in json.loads(gzip.decompress((REF/'m1-network.json.gz').read_bytes()))['records']:
        if row[4]:result.setdefault(str(int(row[0])),[]).append(row)
    return result

def project(lon,lat):return ((lon+180)/360,(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2)

@lru_cache(maxsize=1024)
def trace(route,start,end):
    result=[]
    for row in lines().get(route,[]):
        a,b=row[4];lo=max(min(a,b),min(start,end));hi=min(max(a,b),max(start,end))
        if hi<=lo or a==b:continue
        points=[project(*p) for p in row[3]];lengths=[0]
        for p,q in zip(points,points[1:]):lengths.append(lengths[-1]+math.dist(p,q))
        total=lengths[-1]
        if not total:continue
        left,right=sorted(((lo-a)/(b-a)*total,(hi-a)/(b-a)*total));path=[]
        for i in range(1,len(points)):
            low=max(left,lengths[i-1]);high=min(right,lengths[i]);width=lengths[i]-lengths[i-1]
            if high<low or not width:continue
            for at in (low,high):
                f=(at-lengths[i-1])/width;path.append(tuple(p+(q-p)*f for p,q in zip(points[i-1],points[i])))
        if len(path)>1:result.append(path)
    return result

def nearby(source,target,scale):
    # Spatial bins avoid quadratic comparison on long sections.
    grid={};cell=1000/scale;margin=200/scale
    for path in target:
        for a,b in zip(path,path[1:]):
            for x in range(math.floor((min(a[0],b[0])-margin)/cell),math.floor((max(a[0],b[0])+margin)/cell)+1):
                for y in range(math.floor((min(a[1],b[1])-margin)/cell),math.floor((max(a[1],b[1])+margin)/cell)+1):grid.setdefault((x,y),[]).append((a,b))
    if not source or not grid:return False
    for path in source:
        for a,b in zip(path,path[1:]):
            steps=max(1,math.ceil(math.dist(a,b)*scale/100))
            for i in range(steps+1):
                p=tuple(x+(y-x)*i/steps for x,y in zip(a,b));best=math.inf
                for c,d in grid.get((math.floor(p[0]/cell),math.floor(p[1]/cell)),[]):
                    dx,dy=d[0]-c[0],d[1]-c[1];length=dx*dx+dy*dy;f=max(0,min(1,((p[0]-c[0])*dx+(p[1]-c[1])*dy)/length)) if length else 0
                    best=min(best,math.hypot(p[0]-c[0]-f*dx,p[1]-c[1]-f*dy)*scale)
                if best>200:return False
    return True

def parallel(matches):
    from .route_knowledge_mapping import reference
    refs=reference()[0];first=matches[0]
    # Für die erste Strecke dieselbe Bezugsbreite wie im Browser verwenden.
    latitude=next((p['lat'] for (route,_),rows in refs.items() if route==first['route'] for p in rows),51)
    scale=40075016.686*math.cos(math.radians(latitude))
    paths=[trace(m['route'],m['from_m'],m['to_m']) for m in matches]
    return all(nearby(a,b,scale) and nearby(b,a,scale) for i,a in enumerate(paths) for b in paths[i+1:])
