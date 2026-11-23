# Separate Polish STK reference database

© OpenStreetMap contributors / Geofabrik, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), [attribution](https://www.openstreetmap.org/copyright). This derived database is separate from the German M1/DS100 reference and from private TF records. It contains no user data. The parent `poland-rail` database retains original source railway geometry.

Snapshot: **19 November 2026**. `manifest.json` records all 16 dated regional Geofabrik archive URLs and extracted SHP/DBF checksums. `source.json.gz` retains the transport points and rail metadata used in preparation. Regional extracts can include neighboring border areas. The free transport layer provides **3,366 railway stations/halts** (1,305 stations, 2,061 halts), of which **3,089** have a reference-track projection within 200 m. **277** outside this limit or ambiguous between different levels remain visible but cannot anchor a saved route. Nearest-track association is a geometric aid, not official verification of an operating point or its platform/track.

`PL:N…` identifies the original OSM node. `PL:J…` identifies a deterministic derived graph vertex, **not** an official reporting point, PKP/UIC identifier, DS100 code or line number. There are 53,127 derived junctions and 19,590 endpoints; these include sidings, industrial tracks, source discontinuities and border ends. They must not be described as 72,717 official Polish operating points. The reference is not a complete official PKP PLK operating-point directory. Official reporting-point identities, operational line numbers, mileage and GPS qualification by direction are not supplied by these free shapefiles.

The graph uses source vertices and source layer values. Geometric crossings without shared source vertices do not create connections. Different levels join only at unbranched pairs of dangling endpoints with exactly identical horizontal coordinates. Stations are projected onto the nearest source segment; equal-distance different-level candidates remain unlinked. Degree-two chains are compressed; edge geometry is simplified for rendering while original source rail coordinates are retained separately. Closed components without a retained station/junction/end anchor are not routed. Connectivity and proposed alternatives need checking on the map; a reference connection does not establish operational usability.

Preparation (build-time Shapely 2.x; no GIS server dependency):

```
gzip -dc backend/lokzeitleiste/reference/poland-stk/source.json.gz > /tmp/poland-stk-source.json
python tools/prepare-poland-stk.py --source /tmp/poland-stk-source.json
python tools/build-poland-stk.py
python tools/build-poland-rail.py
```

The last two commands use only Python's standard library and support `--check`. They package a public worker topology, 256-edge geometry chunks and tiled point markers. Android bundles the same public data for offline use. Checksums cover graph, source and generated files. Neither generator awards route knowledge.

Private manual paths are stored in `poland_route_knowledge`, linked to the authenticated TF. Explicit save validates every contiguous edge, source revision, date (at most one year), ownership and modification revision. Stored geometry snapshots keep older reference paths visible. Date-only edits remain possible for old snapshots; geometry changes need the current reference. German imports and GPS originals are untouched. The client currently offers one route variant per leg. Server validation also supports up to three genuinely parallel variants per leg; this does not imply official Polish track or line equivalence.
