# M1-Betriebsstellen: Abgleich vom 17.11.2026

Die hochgeladene `M1 Betriebsstellen.csv` enthält 10.632 Zeilen mit 7.667 unterschiedlichen Kürzeln. Die geografischen Längen-/Breitenspalten (EPSG:4326, Dezimalkomma) werden unverändert als Zahlen übernommen. Die zusätzlich enthaltene WKT-WGS84-Darstellung weicht geringfügig davon ab und wird nicht mit den numerischen Koordinaten vermischt. Prüfsumme und gewählte Koordinatenfelder stehen im Manifest unter `backend/lokzeitleiste/reference/operating-points/`.

## DS100 und GPS

- 42 neue aktive Betriebsstellen ergänzen den Katalog: insgesamt 14.928 Einträge.
- 36 davon bekommen eindeutig zugeordnete Koordinaten: insgesamt 6.486 Referenzpositionen.
- Bestehende Namen und Koordinaten werden erhalten; TF-bestätigte Positionen werden nicht überschrieben.
- Nur aktive Stellen mit eindeutigem normalisiertem Namen und höchstens 25 Metern Abstand zwischen sämtlichen Referenzpunkten bekommen eine gemeinsame GPS-Position. Kein künstlicher Mittelwert.
- 981 Kürzel benötigen wegen Namensabweichungen oder größerer räumlicher Streuung eine gesonderte Prüfung. `review.json` enthält nur diese Fälle. Interne Leerzeichen im Kürzel bleiben erhalten: etwa `WN G` und `WNG` sind unterschiedliche Einträge.
- Stillgelegte, ehemalige oder geplante Betriebsstellen bleiben als entsprechend gekennzeichnete Streckenreferenzen erhalten; sie werden nicht automatisch zu aktiven GPS-Ortsvorschlägen.

Das bestehende Serverupdate legt die Tabelle `railway_operating_points` an und ergänzt die neuen Katalogeinträge einmalig. Referenzkoordinaten bleiben beim Einspielen fehlender Positionen erhalten. Die Android-APK enthält den vollständigen DS100-Katalog und alle streckenbezogenen Punkte; dafür ist keine Netzverbindung nötig. Im geöffneten Webportal können die bereits geladenen Daten offline verwendet werden. Zum erneuten Öffnen der Webseite ist weiterhin eine Verbindung nötig; Android liefert die Daten schon bei der Erstinstallation mit.

## Streckenkunde

Alle 10.632 Quellzeilen bleiben in der komprimierten Referenzquelle erhalten. Identische vollständige Zeilen werden in der Referenztabelle dedupliziert. Mehrere Positionen eines Kürzels auf unterschiedlichen Strecken bleiben getrennt. Die Karte zeigt ab Zoomstufe 10 Betriebsstellenpunkte, ab Zoomstufe 13 deren Kürzel. Durch Antippen oder Tastaturauswahl eines Punkts siehst Du Name, Strecke, Kilometer, Art und Betriebszustand. Die Referenzpunkte sind auch offline verfügbar.

Betriebsstellen und ihre Streckenzuordnungen sind keine persönlichen Fahrten. Die persönliche CSV kann jedoch ausdrücklich importierte Kenntnisse auf diesen Referenzlinien darstellen: VzG-Nummer und beide DS100-Endpunkte müssen zur gleichen Referenzstrecke passen, mit eindeutiger Kilometerlage. Nur der Bereich zwischen Von und Bis wird eingefärbt. Fehlen Teile der Referenzgeometrie, bleiben diese Lücken frei. Fehlende oder mehrdeutige Zuordnungen bleiben als offene Fälle in der Liste sichtbar.

Importierte Kenntnisse sind gestrichelt dargestellt und separat ausblendbar: Grün für `streckenkundig`, Blau für `wird erworben`, Rot für `abgelaufen` oder ein überschrittenes angegebenes Gültigkeitsdatum. Fehlende Gültigkeitsdaten werden nicht erfunden. Diese Darstellung ist von den durch GPS belegten Richtungszählern und Altersfarben getrennt. Auch bereits früher importierte Listen bekommen beim erneuten Laden die Kartenzuordnung; ein erneuter Import ist dann nicht nötig.

Referenzdaten allein Sie erzeugen keine GPS-Aufzeichnungen, Fahrtdaten, Richtungszähler oder Streckenkenntnisnachweise. Farben aus echten aufgezeichneten Fahrten behalten ihre bestehenden Regeln.

## Persönliche Kenntnis-CSV importieren

1. Aktualisiere zuerst den Server und bei Android auch die vorhandene App.
2. Melde Dich im gewünschten TF-Konto an und öffne **Stecken-, BR- und Ortskenntnisse → Streckenkenntnis**.
3. Die Importfunktion steht direkt oberhalb der Karte. Wähle Deine CSV-Datei. Die Vorschau öffnet sich automatisch; Du kannst sie auch mit **Importvorschau** erneut aufrufen.
4. Prüfe Deinen Namen, Deine Tf-Nummer und die Anzahlen neuer, vorhandener und abweichender Einträge.
5. Bestätige mit **Für diesen TF übernehmen**. Erst jetzt wird gespeichert.

Import und Vorschau brauchen den erreichbaren aktualisierten Server. Die persönliche Liste wird nach dem Laden für Dein Konto offline gespeichert. Ursprüngliche Status-, Gültigkeits- und Erwerbsangaben bleiben erhalten, auch Platzhalter wie `0000-00-00`. Die ursprünglichen CSV-Felder werden nicht durch Referenzdaten ersetzt. Wiederholter Import erzeugt keine Duplikate; abweichende vorhandene Angaben werden erhalten. Persönliche Dateien gehören nicht in das öffentliche Repository oder in die APK.

## Reproduzierbarkeit

`python tools/build-operating-points.py --check` prüft die Referenzquelle. `python tools/build-station-catalog.py --check` prüft den erzeugten Offlinekatalog. Die komprimierte Quelle enthält nur öffentliche Referenzangaben, keine persönlichen GPS- oder Kenntnisdaten.
