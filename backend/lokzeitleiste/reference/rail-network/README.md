# M1-Streckennetz als Offline-Referenz

Quelle ist die am 17.11.2026 bereitgestellte Datei **M1 Streckennetz.csv.zip** mit genau einer Nutzdatei **M1 Streckennetz.csv**. Das Empfangsdatum ist kein Aktualitätsdatum des Netzes. Die CSV enthält keinen Datenstands- oder Lizenzhinweis; solche Angaben werden nicht hinzuerfunden. Originaldatei-SHA256 und Statistik stehen in `manifest.json`.

Die 62.979.144 Byte große CSV enthält 33.425 Datensätze zu 1.549 Streckennummern. Verwendet wird ausschließlich die ausdrücklich als **WKT WGS84 (EPSG 4326)** bezeichnete Geometriespalte, mit Längengrad vor Breitengrad. GK- und UTM-Spalten werden nicht geraten oder zusätzlich transformiert. Semikolon, Dezimalkomma in Kilometrierung, LINESTRING und getrennte MULTILINESTRING-Teile werden verarbeitet.

`m1-network.json.gz` ist die kompakte gemeinsame Eingabequelle: Streckennummer/-kurzname, Status, auf sechs Nachkommastellen gerundete WGS84-Geometrie und Kilometrierungsgrenzen. Identische Geometrien derselben Strecke, desselben Status und derselben Kilometrierung werden zusammengefasst. Getrennte WKT-Teile werden nie verbunden. Weil die CSV für diese Teile keine separaten Kilometrierungsgrenzen enthält, erhalten sie keine erfundene Kilometrierung und geben keine automatische Fahrtengutschrift.

`tools/build-rail-network.py` erzeugt das versionierte öffentliche JS-Bündel, seine HTTP-Gzip-Variante und das Manifest. Das Netz verwendet quantisierte Web-Mercator-Koordinaten, eine Detailstufe mit 2 m projektierter Vereinfachungstoleranz und eine Übersicht mit 80 m. Endpunkte und getrennte Linien bleiben erhalten. Der HTTP-Gzip-Inhalt ist identisch zum unkomprimierten Android-Asset. In Android werden keine zusätzlichen Netz-Downloads benötigt.

```bash
python tools/build-rail-network.py
python tools/build-rail-network.py --check
# Neuimport derselben Quellstruktur:
python tools/build-rail-network.py --source '/Pfad/M1 Streckennetz.csv.zip'
```

Die privaten GPS-Aufzeichnungen werden weder verändert noch in dieses öffentliche Bündel geschrieben. `route-coverage.js` ordnet sie lokal dem Netz zu: 100-m-Kilometrierungsabschnitte je Streckennummer kombinieren parallele Gleise derselben Strecke. Pro Zugfahrt/Abschnitt/Richtung wird höchstens eine Fahrt gewertet. Mindestens 80 % des im Referenznetz vorhandenen Abschnitts müssen eindeutig abgedeckt sein. Abweichungen über 50 m, stark abweichende Richtung, mehrdeutige Streckennummer oder Kilometrierung und GPS-Lücken erzeugen keine Gutschrift. Grün erfordert mindestens zwei verschiedene Zugfahrten je Richtung. Ohne eindeutige Zuordnung gibt es kein Grün. Bekannte GPS-Fahrtdaten können auch unzugeordnete Spuren orange oder rot färben; ohne Datum bleiben sie blau. Die Farbgebung ist keine formale Qualifikationsverwaltung.


Ab 0.26.62 übertragen lokale und serverseitige Auswertungen die vorhandenen GPS-Zeitstempel als dritte Koordinate. Die API liefert bei `dates=1` nur `timed_segments`; ältere Aufrufer erhalten unverändert `segments` ohne Zeitspalten. Es werden keine Fahrtdaten aus Aufrufzeit oder Datenbank-Änderungszeit erfunden. Je 100-m-Abschnitt gilt das jüngste Datum einer angerechneten Fahrt in beliebiger Richtung. Maßgeblich sind Kalendertage in Europe/Berlin: 0–180 Blau/Grün nach Fahrtenzahl, 181–365 Orange, ab 366 Rot. Eine fehlende Zeitangabe erzeugt kein frisches Grün. CSV-Metadaten ändern nur die Strichelung unbefahrener schwarzer Linien. Ein Tageswechsel aktualisiert die Farben einer geöffneten Karte, ohne neue Fahrten zu zählen.
