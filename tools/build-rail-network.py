# Bereitet öffentliche Eisenbahn-Referenzdaten aus den eingecheckten Quellen reproduzierbar auf.
"""Import the supplied M1 CSV and reproducibly build the offline rail map bundle.

The canonical gzip retains only map geometry and route identity/status, not the
three redundant coordinate representations in the 63 MB source CSV.
"""
import argparse,csv,gzip,hashlib,io,json,math,re,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'backend/lokzeitleiste/reference/rail-network'
SOURCE=REF/'m1-network.json.gz'
MANIFEST=REF/'manifest.json'
OUTPUT=ROOT/'backend/lokzeitleiste/static/rail-network-data.js'
COMPRESSED=OUTPUT.with_suffix('.js.gz')
LOADER=OUTPUT.with_name('rail-network.js')
SCALE=100_000_000
WORLD=40075016.68557849

def parse_wkt(value):
    value=value.strip()
    if value.startswith('LINESTRING '):parts=[value[len('LINESTRING '):].strip()]
    elif value.startswith('MULTILINESTRING '):
        body=value[len('MULTILINESTRING '):].strip()
        if not body.startswith('(') or not body.endswith(')'):raise ValueError('Malformed multi-line')
        parts=re.split(r'\)\s*,\s*\(',body[1:-1].strip()[1:-1])
    else:raise ValueError('Unsupported WKT geometry')
    lines=[]
    for part in parts:
        points=[]
        for pair in part.strip('() ').split(','):
            values=pair.split()
            if len(values)!=2:raise ValueError('Expected lon lat in EPSG:4326')
            lon,lat=map(float,values)
            if not math.isfinite(lon) or not math.isfinite(lat) or not -180<=lon<=180 or not -85<=lat<=85:raise ValueError('Invalid coordinate')
            # Nur im Bereich unter einem Meter runden und getrennte Abschnitte getrennt erhalten.
            point=[round(lon,6),round(lat,6)]
            if not points or point!=points[-1]:points.append(point)
        if len(points)<2:raise ValueError('Line has fewer than two distinct points')
        lines.append(points)
    return lines

def project(point):
    lon,lat=point
    return [round((lon+180)/360*SCALE),round((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*SCALE)]

def simplify(points,tolerance):
    keep={0,len(points)-1};stack=[(0,len(points)-1)];limit=tolerance*tolerance
    while stack:
        first,last=stack.pop();ax,ay=points[first];bx,by=points[last];dx,dy=bx-ax,by-ay;length=dx*dx+dy*dy
        farthest=limit;chosen=None
        for i in range(first+1,last):
            px,py=points[i];fraction=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/length)) if length else 0
            squared=(px-ax-fraction*dx)**2+(py-ay-fraction*dy)**2
            if squared>farthest:farthest=squared;chosen=i
        if chosen is not None:keep.add(chosen);stack.extend([(first,chosen),(chosen,last)])
    return [points[i] for i in sorted(keep)]

def import_csv(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            files=[i for i in z.infolist() if i.filename.lower().endswith('.csv') and not i.filename.startswith('__MACOSX/')]
            if len(files)!=1:raise ValueError('Expected exactly one CSV')
            raw=z.read(files[0]);name=Path(files[0].filename).name
    else:raw=path.read_bytes();name=path.name
    records=[];source_count=0;routes=set();seen=set();duplicates=0;bounds=[180,90,-180,-90]
    for row in csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';'):
        source_count+=1;code=row['Streckennummer'].strip()
        if not code.isdigit():raise ValueError(f'Invalid route number in row {source_count}')
        routes.add(code)
        state=1 if row['Bauzustand'].strip()=='im Bau' else 2 if row['DB Betrieb'].strip()=='Nicht in DB Netz Betrieb' else 0
        parts=parse_wkt(row['WKT WGS84 (EPSG 4326)'])
        start=round(float(row['km_von_km'].replace(',','.'))*1000+float(row['km_von_m'].replace(',','.')))
        end=round(float(row['km_bis_km'].replace(',','.'))*1000+float(row['km_bis_m'].replace(',','.')))
        for points in parts:
            # Disconnected WKT parts do not supply separate mileage limits.
            # Die Abschnitte anzeigen, aber aus fehlenden Kilometerangaben keine Fahrtenzählungen ableiten.
            mileage=[start,end] if len(parts)==1 and start!=end else None
            if points[-1]<points[0]:
                points.reverse()
                if mileage:mileage.reverse()
            identity=(code,state,tuple(map(tuple,points)),tuple(mileage) if mileage else None)
            if identity in seen:duplicates+=1;continue
            seen.add(identity)
            for lon,lat in points:bounds=[min(bounds[0],lon),min(bounds[1],lat),max(bounds[2],lon),max(bounds[3],lat)]
            records.append([code,row['Streckenkurzname'].strip(),state,points,mileage])
    records.sort(key=lambda row:(row[0],row[2],row[3]))
    data=dict(schema=2,source=dict(name=name,sha256=hashlib.sha256(raw).hexdigest(),crs='EPSG:4326',source_rows=source_count,route_count=len(routes),line_count=len(records),duplicates_removed=duplicates,bounds=bounds),records=records)
    REF.mkdir(parents=True,exist_ok=True)
    SOURCE.write_bytes(gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))

def build():
    raw=SOURCE.read_bytes();data=json.loads(gzip.decompress(raw));routes=sorted({(r[0],r[1]) for r in data['records']});indices={value:i for i,value in enumerate(routes)};lines=[]
    for code,name,state,coords,mileage in data['records']:
        projected=[project(point) for point in coords]
        detail=simplify(projected,2*SCALE/WORLD);overview=simplify(detail,80*SCALE/WORLD)
        bounds=[min(p[0] for p in projected),min(p[1] for p in projected),max(p[0] for p in projected),max(p[1] for p in projected)]
        lines.append([indices[(code,name)],state,bounds,[n for p in detail for n in p],[n for p in overview for n in p],mileage])
    bundle=dict(schema=2,scale=SCALE,source=data['source'],routes=routes,lines=lines)
    script='// Erzeugt durch tools/build-rail-network.py: öffentliche M1-Referenzgeometrie ohne persönliche GPS-Daten.\nwindow.RailNetworkSeed='+json.dumps(bundle,ensure_ascii=False,separators=(',',':'))+';\n'
    manifest=dict(schema=2,source=data['source'],canonical_sha256=hashlib.sha256(raw).hexdigest(),bundle_sha256=hashlib.sha256(script.encode()).hexdigest(),bundle_bytes=len(script.encode()),detail_points=sum(len(row[3])//2 for row in lines),overview_points=sum(len(row[4])//2 for row in lines),detail_tolerance_projected_m=2,overview_tolerance_projected_m=80)
    # Darstellungsänderungen dürfen gespeicherte Streckenreferenzen nicht ungültig machen.
    previous=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    manifest['reference_revision']=previous.get('reference_revision',previous.get('bundle_sha256')) if previous.get('canonical_sha256')==manifest['canonical_sha256'] else manifest['canonical_sha256']
    return script,json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.source:
        if args.check:parser.error('--source and --check cannot be combined')
        import_csv(args.source)
    script,manifest=build()
    revision=json.loads(manifest)['reference_revision']
    loader=LOADER.read_text()
    if not re.search(r"const REVISION='[^']+';",loader):raise ValueError('Missing rail loader revision')
    updated_loader=re.sub(r"const REVISION='[^']+';","const REVISION='"+revision+"';",loader)
    if args.check:
        if updated_loader!=loader:raise SystemExit('Offline rail loader revision is stale')
        if OUTPUT.read_text()!=script or MANIFEST.read_text()!=manifest or gzip.decompress(COMPRESSED.read_bytes())!=script.encode():raise SystemExit('Offline rail bundle is stale')
    else:OUTPUT.write_text(script);COMPRESSED.write_bytes(gzip.compress(script.encode(),mtime=0));MANIFEST.write_text(manifest);LOADER.write_text(updated_loader)
    data=json.loads(manifest);print(f"M1 rail network: {data['source']['source_rows']} source rows / {data['source']['route_count']} routes / {data['source']['line_count']} lines / {data['bundle_bytes']} bundle bytes")
if __name__=='__main__':main()
