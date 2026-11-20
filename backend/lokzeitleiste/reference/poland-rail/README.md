# Poland railway reference

© OpenStreetMap contributors, distributed by Geofabrik. This separate derived database and its generated tiles are licensed under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). [OSM attribution and licence](https://www.openstreetmap.org/copyright).

`manifest.json` lists all 16 dated public source archives, checksums of the extracted railway SHP/DBF files, and the canonical database checksum. Only `fclass=rail` geometry is retained; identical OSM geometry parts from overlapping extracts are deduplicated. This can include service/industrial tracks. It is a visual reference, not official PKP PLK operating information or proof of route knowledge. OSM identifiers and source coordinates remain in `poland.json.gz`. It contains no user records.

Run `python tools/build-poland-rail.py` to regenerate a coarse overview and ~20 m visual detail geometry, divided into world-grid tiles. `--check` verifies exact reproducibility. Original source coordinates remain unchanged in the separate ODbL database; the German M1 database and user qualifications are not merged into it.
