# Prüfung und Betrieb

Web 0.28.12 erweitert bestehende Abläufe. Die Anwendung schreibt keine neuen Apache-, MariaDB-, Mail- oder Signierungseinstellungen.

## Karten und polnische Suche

Der Schalter „Polnisches Streckennetz“ in Streckenkenntnis und „STK-anlegen o. bearbeiten“ steuert das polnische Netz unabhängig von der Sprache. In der STK-Erfassung wählt er auch den Suchbestand und Editor. Die Einstellung bleibt lokal gespeichert. Der öffentliche polnische Suchkatalog ist in Android enthalten. Namen funktionieren auch ohne polnische Sonderzeichen. Abgeleitete unbenannte Netzknoten sind über die Karte und ihre PL:J-Kennung erreichbar. PL-Kennungen sind OSM-Referenzen, keine DS100-, PKP- oder UIC-Kennungen. 277 nicht eindeutig einem Gleis zugeordnete Punkte bleiben gesperrt. Quellen und Grenzen stehen in der integrierten Hilfe und unter `backend/lokzeitleiste/reference/poland-stk/README.md`.

Berechnungen erfolgen im Hintergrund. Kacheln, räumlicher Markerindex, sichtbare Geometrie und begrenzte Beschriftungen verringern die Arbeit pro Kartenbewegung. Unter „Betatest-Diagnose“ sind die auf dem jeweiligen Gerät gemessenen Zeiten mit Anzahl, Median, 95-Prozent-Wert und Maximum sichtbar. Eine Messung auf einem echten Tablet entsteht erst bei dessen Benutzung; Cloud-Messungen ersetzen diese Messung nicht.

## Übertragungen und Fehler

Der gemeinsame Status zeigt „Lokal gespeichert“, „Zum Senden vorgemerkt“, „Synchronisiert“ und „Prüfung erforderlich“. Die Liste enthält die offenen Aufträge des angemeldeten TF. Eine verlorene Serverbestätigung führt nicht zu einer stillen erneuten POST-Übertragung. Der betreffende Bestand muss zuerst geprüft werden. Bei Berichtfehlern öffnet „Eintrag öffnen“ den lokalen Bericht und erhält die Feldadresse für die rote Markierung. Andere aktuelle Eingaben werden vorher gesichert. Laufende GPS-Erfassungen werden nicht durch einen erzwungenen Berichtwechsel unterbrochen.

## Arbeitsberichte prüfen

In der Verwaltung zeigt der Eingang den Prüfstatus. „In Prüfung“ beginnt die Prüfung. „Freigegeben“ ist erst danach möglich. Die Entscheidung gilt für Berichtsversion und Inhaltsprüfsumme; eine spätere Inhaltsänderung setzt die Anzeige auf „Eingegangen“ zurück. Rückgaben verwenden den bestehenden kommentierten Korrekturablauf. Vorherige PDFs und Prüfentscheidungen bleiben nachvollziehbar. Rechte zum Lesen und zum Prüfen sind getrennt.

## DS100-Korrekturen

„Prüfung und Betrieb → DS100-Koordinaten prüfen“ zeigt TF-Korrekturen mit Herkunft, vorheriger Position, Vorschlag, aktuellem Stand und Verlauf. Die bereits vom TF bestätigten Koordinaten sind wie bisher zunächst angewandt. „Verwerfen“ stellt den vorherigen Stand nur wieder her, wenn zwischenzeitlich keine andere Positionsänderung erfolgt ist. Eine Rücknahme erzeugt eine neue Katalogrevision, damit andere Geräte sie laden. Die vorhandene TF-Bestätigung und der zusätzliche Abgleich bei mehr als 1.000 Metern bleiben erhalten.

## Ablaufübersicht

TF und berechtigte Sachbearbeiter verwenden dieselbe TF-bezogene Auswertung für Strecken, Orte und Baureihen. Sie unterscheidet gültig, in den nächsten drei Monaten ablaufend, abgelaufen und fehlendes Gültigkeitsdatum. Filter, Suche und seitenweises Laden begrenzen die Anzeige. Bestätigte importierte Kenntnisse bleiben führend. Fehlende Daten werden nicht durch erfundene Fahrten oder Nachweise ersetzt.

## Sicherungen und Prüfung

Der vorhandene Worker `ctlsoftware-test-worker.service` plant standardmäßig einmal täglich eine Sicherung. Ein Administrator kann dies unter „Prüfung und Betrieb → Sicherungen“ ausschalten oder eine zusätzliche Sicherung vormerken. Die Webanfrage sichert nicht selbst; der Worker führt den Auftrag aus. Ein unterbrochener oder fehlgeschlagener Lauf wird nicht als geprüft angezeigt.

Ablage: `_rail_backups` unter dem bestehenden `LOKZEITLEISTE_FILES_ROOT`. Das Verzeichnis ist nur für den Dienstbenutzer zugänglich (0700), die Archive haben 0600. Gesichert werden die Anwendungstabellen und die Benutzerverzeichnisse TF, VW und WGM. Eine konsistente Lesetransaktion hält den Datenbankstand während des Exports fest. Die spätere Prüfung kontrolliert auch, ob alle in der gesicherten Dokumententabelle referenzierten Dateien mit passenden Größen und Prüfsummen im Archiv vorhanden sind. Änderungen während der Dateikopie können die Prüfung fehlschlagen lassen; das Archiv wird dann nicht als gültig übernommen.

Die Wiederherstellungsprüfung importiert alle Tabellen in eine **isolierte temporäre SQLite-Datenbank**, prüft Fremdschlüssel, Datensatzanzahlen und Prüfsummen und stellt alle Dateien in einem getrennten temporären Verzeichnis wieder her. Sie beschreibt keine laufende Datenbank und keine produktiven Dateien. Das Ergebnis erscheint mit Zeitpunkt und Umfang in der Verwaltung. Die letzten sieben geprüften Sicherungen bleiben erhalten.

Die Prüfung lässt sich mit dem Python der installierten Anwendung erneut ausführen:

```bash
python -m lokzeitleiste.backups --verify /absoluter/pfad/zur/sicherung.zip
```

Diese portable Wiederherstellung prüft Tabellen und Dateien. Sie ersetzt **keine Wiederanlaufprobe auf einem zweiten MariaDB-Server**, keine externe Sicherungskopie und keine Sicherung der Betriebssystem-/Webserverkonfiguration. Das Archiv bleibt auf dem Server; es wird weder in GitHub noch in die Android-App übernommen. Zugriff und externe Aufbewahrung liegen beim Serverbetrieb.

## Diagnosepaket

„Betatest-Diagnose → Diagnosepaket herunterladen“ erzeugt erst auf Klick eine lokale JSON-Datei. Sie enthält Version, grobe Geräte-/Browserangaben, Laufzeitstatistik und technische Fehlerarten beziehungsweise HTTP-Statuscodes. Passwörter, Token, Namen, Formulare, Suchbegriffe, URLs mit Parametern, persönliche GPS-Punkte und rohe Fehlertexte werden nicht aufgenommen. Es erfolgt kein automatischer Upload. Die Datei kann vor einer Weitergabe geprüft werden.
