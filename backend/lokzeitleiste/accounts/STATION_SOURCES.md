# Bahnhofsdaten und Länder

Die mitgelieferte Bahnhofsliste ist ein auf Code und Name reduzierter Auszug der offenen DB-Netz-Betriebsstellenliste **Stand April 2018**. Berücksichtigt sind aktive Bahnhöfe, Haltepunkte und Bahnhofsteile laut damaligem Betriebszustand. Diese Liste ist keine aktuelle betriebliche Referenz.

- Urheber: **Deutsche Bahn AG**, Datenlizenz **CC BY 4.0**, <https://creativecommons.org/licenses/by/4.0/>
- Ursprüngliche Quelle: <https://download-data.deutschebahn.com/static/datasets/betriebsstellen/DBNetz-Betriebsstellenverzeichnis-Stand2018-04.csv>
- Abgerufene unveränderte Kopie: <https://github.com/fourplusone/ds100/blob/master/DBNetz-Betriebsstellenverzeichnis-Stand2018-04.csv>
- Änderungen: Auswahl von Bahnhofstypen und aktivem Betriebszustand, Reduktion auf Code/Name, Normalisierung von Leerzeichen, Zusammenführung gleicher Codes.
- Aktuelle offizielle Liste: <https://www.dbinfrago.com/web/schienennetz/betrieb/allgemeine-betriebsinformationen/betriebsstellen-12592996> (bei Prüfung am 11.10.2026: XLSX Stand 31.08.2026). Die Datei konnte in der Entwicklungsumgebung nicht heruntergeladen werden.

Aktualisierung im Container nach Bereitstellung der offiziellen CSV/XLSX-Datei:

```sh
python -m lokzeitleiste.accounts.import_stations /srv/data/betriebsstellen.xlsx --code-column 'Abk' --name-column 'Name'
```

Spaltennamen an die tatsächlichen Überschriften anpassen; optional `--sheet`. Vor dem Commit werden Datensätze validiert. Bestehende Codes werden aktualisiert, neue angelegt. Bereits zugewiesene Codes bleiben erhalten, damit ältere Profile nicht ungültig werden. Die aktuelle Liste und ihre Nutzungshinweise werden vom Administrator bereitgestellt; es werden keine erfundenen aktuellen Codes verwendet.

`countries.json` umfasst die 249 ISO-3166-Länder und Gebiete aus der IANA-tzdata-Länderliste, mit lokalisierten Namen aus Unicode CLDR/ICU (`Intl.DisplayNames`) für Deutsch, Englisch, Polnisch, Russisch, Türkisch, Arabisch und Spanisch. Die Auswahl speichert den zweistelligen ISO-Code.


## Referenzkoordinaten ab 0.26.50 (Prüfung 15.11.2026)

Für **5.408** der unveränderten **13.720** mitgelieferten DS100-Stellen sind WGS84-Koordinaten in `station_coordinates.json` hinterlegt. `station_coordinates_review.txt` enthält ausschließlich die **857** Kürzel mit mehreren Referenzpunkten oder abweichenden Namen: ein Kürzel pro Zeile, ohne Kopfzeile oder weitere Angaben. Diese Prüffälle erhalten keine automatisch gewählte Position.

### Quelle und Lizenz

- Urheber: **DB InfraGO AG**, Infrastrukturdaten, laut GovData **Stand Mai 2026**.
- Metadatensatz: <https://data.gov.de/suche/daten/infrastrukturdaten-der-db-infrago>
- Verwendeter Download: <https://mobilithek.info/mdp-api/files/aux/922109165921083392/Infrastrukturdaten.zip>
- Datei im ZIP: `M1 Betriebsstellen.csv`, 10.632 Zeilen.
- Lizenz laut Ressourcen-Metadaten: **CC BY 4.0**, <https://creativecommons.org/licenses/by/4.0/>.
- Änderungen: Auswahl passend zum mitgelieferten Stationskatalog; Übernahme der Spalten „Geographische Breite (EPSG 4326)“ und „Geographische Länge (EPSG 4326)“; Reduktion auf Code, Katalognamen, Quellenname und Koordinaten; Aufnahme von Provenienz und Prüfwerten. Keine geschätzten Ortsmittelpunkte. Quellen-URL, Datenstand, Lizenz und SHA-256 der Ursprungs-CSV sind zusätzlich in der JSON-Datei enthalten.

### Auswahl

DS100-Kürzel stimmen nach Vereinheitlichung mehrfacher Leerzeichen überein; Leerzeichen werden nicht vollständig entfernt. Namen stimmen nach Unicode-, Groß-/Kleinschreibungs-, Satzzeichen- und Leerzeichennormalisierung überein. Es gibt keine unscharfe Namenszuordnung und keine Übernahme der Koordinaten des Hauptbahnhofs für eine anders bezeichnete Unterstelle. Alle berücksichtigten Quelldatensätze sind „in Betrieb“. Der größte Abstand zwischen ihren Referenzpunkten beträgt höchstens **25 Meter**. Das ist eine Konsistenzschwelle, keine zugesicherte Messgenauigkeit. Bei mehreren konsistenten Punkten bleibt der erste tatsächliche Quellenpunkt erhalten, kein berechneter Mittelpunkt.

798 Stellen brauchen wegen größerer Punktabstände eine Prüfung; 59 weitere wegen Namensabweichungen. 20 Stellen führt die Quelle nicht als in Betrieb; 7.435 haben in dieser offiziellen Quelle keinen Treffer. Sie werden nicht ergänzt. Ältere Zusatzquellen lieferten sieben Kandidaten innerhalb dieser 7.435; diese sind ausdrücklich nicht Teil des übernommenen Datenbestands.

### Bestehende Installation

`init_db` legt über `create_all` die zusätzliche Tabelle `railway_station_coordinates` an und ruft nach `seed_stations` den Import `seed_coordinates` auf. Bestehende Tabellen müssen nicht geändert werden. Die ganze Datei wird vor dem ersten Schreibzugriff validiert. Eingefügt werden ausschließlich fehlende Positionen von bereits vorhandenen Codes mit passendem Namen. Bereits gespeicherte Koordinaten werden nie überschrieben, manuell geänderte Namen nicht zurückgesetzt und neue Stationscodes nicht erfunden. Die aufrufende Update-Routine kontrolliert Commit/Rollback. Ein erneuter Updateaufruf ist idempotent. Auf einem unveränderten vollständigen Katalog werden genau 5.408 Positionen ergänzt; ein abweichender Serverbestand kann weniger ergeben.

Die geschützte TF-Katalogsuche `/api/v1/tf/stations/catalog` liefert zusätzlich `coordinates` mit `latitude`, `longitude`, `crs`, `source_url` und `source_date` oder `null`. Bei einem nachträglich anders benannten Katalogeintrag wird eine nicht mehr passende gespeicherte Position nicht ausgegeben. Persönliche Stationsnotizen, Kontakte und Pläne bleiben unverändert. Die GPS-Aufzeichnung und die manuelle Übernahme ihrer Halte werden nicht geändert; eine automatische Zuordnung von GPS-Halten ist damit nicht eingeführt.

Der bestätigte Apache-/MariaDB-Server übernimmt die Ergänzungen mit dem bestehenden Updateweg, ohne Neuinstallation oder Änderung der Serverkonfiguration. Laufzeit-Downloads externer Daten sind nicht erforderlich.
