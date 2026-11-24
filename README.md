# LokZeitleiste v0.28.18

**0.28.18 / Android 0.28.18.25:** Art–Grund-Zuordnungen als n:m-Beziehung in den Stammdaten mit gefilterter Auswahl im Arbeitsbericht. Offene Übertragungen zeigen die tatsächlichen lokalen Berichte/GPS-Aufzeichnungen und öffnen den zugehörigen Bericht; die Betatest-Diagnose erscheint nur für TF 787117. Kurznachrichten mit Chatansicht, Suche, Lesebestätigung, Anhängen und lokalen Textentwürfen. Neues Dienstplan-Modul für Personalplanung und TF: Excel-Vorschau, bestätigte Spalten-/TF-Zuordnung und private Anzeige der geplanten Dienste, auch als Fenster im Arbeitsbericht. Bestehende Berichte und Stammdaten bleiben erhalten. Die optionale Tfz-Auswahl liest offline den lokalen Bestand ohne Netzabfrage.

### Dienstplan und Art–Grund-Zuordnung

Die Verwaltung öffnet **Dienstplan** mit den vorhandenen Planungsrechten (Import ab Schreibrecht). Importiere `.xls` oder `.xlsx`, wähle Tabellenblatt und Kopfzeile; `0` erkennt die mitgelieferte CTL-Struktur automatisch. Die Spaltenzuordnung ist vor dem Bestätigen prüfbar. Bei dieser Struktur werden A, B, O, Q, S und T nicht übernommen. Zugart/Pause, betriebliche Bahnhöfe, Vor-/Abschlusscodes, Zeiten, Tfz, Umlaufname und Kommentar bleiben erhalten. Baureihennummern zwischen Nachname und Vorname werden nur für den Namensabgleich entfernt; eindeutige Kontotreffer sind sichtbare Vorschläge, mehrdeutige Treffer bleiben unzugeordnet. Erst **Import bestätigen** veröffentlicht die ausgewählten Zeilen für die zugeordneten TF. Es entstehen keine tatsächlichen Arbeitsberichte. Wiederholung desselben bestätigten Imports erzeugt keine Duplikate. Die persönliche Beispieldatei gehört nicht ins Repository oder in die APK.

TF öffnen **Dienstplan** über die eigene Kachel oder im Arbeitsbericht als Fenster. Vor-/Abschlusscodes erscheinen mit CTL; „keiner“ und „weiter“ bleiben Hinweise. Bereits geladene Pläne sind in Android offline lesbar. In den **Stammdaten** ordnest Du je Art beliebig viele Gründe zu; derselbe Grund darf zu mehreren Arten gehören. Zur bestandsschonenden Einführung bleiben zunächst alle bisherigen Kombinationen zugeordnet. Neue Stammdaten ordnest Du ausdrücklich zu. Gespeicherte historische Kombinationen bleiben bearbeitbar.

**0.28.17 / Android 0.28.17.22:** Der Standzeiten-Hinweis zeigt den aus Mein Konto übernommenen Schwellwert der Aufzeichnung statt einer festen Zwei-Minuten-Angabe. „Start Stand“ ist im Hinweis grün hervorgehoben. Die Erfassungsregeln werden dadurch nicht verändert.

**0.28.16 / Android 0.28.16.21:** Optionale Tfz-Auswahl vor dem GPS-Start mit Offline-Zuordnung. Abgeschlossene synchronisierte Fahrten werden getrennt verdichtet und in der Verwaltung beim Tfz über „GPS-Fahrten“ angezeigt: Datum, Uhrzeit, Tf-Nummer, Von/Bis (DS100), Gesamt km. Die GPS-Schätzung verändert keinen Stammdaten-Kilometerstand. Zuerst den Server aktualisieren, damit Zuordnung und neue Tabelle unterstützt werden.

**0.28.15 / Android 0.28.15.20:** Monatsberichte als erster Reiter, kompakter Dienstbeginn-/Dienstende-/Pausenhinweis bei Zugfahrten und 8h-Ausbleibe als DS-Vorauswahl. Polnisches Streckennetz unabhängig von der Sprache per Schalter anzeigen; polnische Startorte suchen, dorthin zoomen und Verläufe punktweise zeichnen, speichern und bearbeiten.

**0.28.14 / Android 0.28.14.19:** Pflichtfelder werden mit kleinem Stern am Label und der Erklärung „* Pflichtfeld“ gekennzeichnet, einschließlich dynamischer Formulare und nativer Android-Eingaben. Rote Rahmen erscheinen bei festgestellten Eingabefehlern statt bereits beim Öffnen leerer Pflichtfelder. GPS-Zielbahnhöfe verlängern die Ortskenntnis erst nach einer ausdrücklichen Ja/Nein-Abfrage; die Entscheidung bleibt offline erhalten.

**0.28.13 / Android 0.28.13.18:** Kartenverschiebung mit einem und zwei Fingern korrigiert. Die Übergabe der Berührung vom SVG-Kartenelement an den Kartencontainer verwirft die Geste nicht mehr. Nach dem Anheben eines Fingers kannst Du mit dem verbleibenden Finger weiter verschieben.

**0.28.12 / Android 0.28.12.17:** Netzabhängige polnische Ortssuche und erweiterte manuelle STK-Erfassung mit parallelen Varianten, Weiterzeichnen und Verbindungsvorschlägen. Gemeinsamer Übertragungsstatus und datensparsamer Diagnoseexport, Prüfablauf für Arbeitsberichte, DS100-Prüfliste, gemeinsame Ablaufübersicht sowie tägliche private Sicherung mit isolierter Datenbank-/Dateiwiederherstellung. Betrieb und Grenzen: [Prüfung und Sicherung](docs/QUALITY-OPERATIONS.md).

**0.28.11 / Android 0.28.11.15:** Polnische Bahnhofs-/Haltepunkte und abgeleitete Netzknoten in der polnischen Karte. Eigene polnische STK-Verläufe mit Offline-Suche, Routenberechnung im Hintergrund, Speichern, Bearbeiten und Löschen je TF. Bei Sprache Polski im STK-Modul das Netz Polen · OSM wählen. 3.366 Stations-/Haltepunkte, davon 3.089 geometrisch zugeordnet; 277 ungeklärte Punkte bleiben gesperrt. Kein vollständiges amtliches Betriebsstellenverzeichnis. Quellen, Grenzen und Reproduktion: [Polnische STK-Referenz](backend/lokzeitleiste/reference/poland-stk/README.md).

**0.28.9 / Android 0.28.9.11:** Überflüssigen Unterreiter Streckenkenntnis anzeigen entfernt. Karte, Bestandsanzeige und Import stehen direkt im Reiter Streckenkenntnis; das eigene STK-Modul bleibt erhalten.

**0.28.8 / Android 0.28.8.10:** STK-anlegen o. bearbeiten als eigenes TF-Modul mit Kachel. Tabellen für Auswahl und gespeicherte Verläufe mit Sortierung, 10/25/50/100/alle Zeilen, Seitennavigation und Direktsprung. Die Kenntnisansicht behält Streckenkenntnis anzeigen unter Streckenkenntnis.

**0.28.7 / Android 0.28.7.9:** Zusätzliches polnisches OSM-/Geofabrik-Streckennetz, ausschließlich bei Sprache Polski sichtbar. Offline-Übersicht und räumlich getrennte Detailkacheln schonen Tablet-Speicher und Darstellung. Deutscher M1-Bestand und Kenntnisse bleiben getrennt.

**0.28.6 / Android 0.28.6.8:** Schlichter gemeinsamer Offline-Hintergrund mit Ortsnamen für GPS, Demo und Streckenkenntnisse. Keine Online-Hintergrundkacheln; Ortsnamen werden nach Zoom und Sichtbarkeit begrenzt. Quellen: Natural Earth (Public domain) und GeoNames (CC BY 4.0).

**0.28.5 / Android 0.28.5.7:** Eigene manuelle Verläufe löschen sowie abgeschlossene eigene GPS-Aufzeichnungen auswählen, isoliert anzeigen und als Von-bis-Verlauf manuell bestätigen. Erst eine separate Online-Prüfung und Bestätigung entfernt das GPS-Original auf Server und diesem Gerät; laufende/geänderte Aufzeichnungen, ungesendete Änderungen und unvollständige Abdeckung verhindern die Bereinigung. Kompakte Kenntnisse und bereits in Berichte übernommene Dienst-/Zugdetails bleiben erhalten; betroffene GPS-Demos werden widerrufen. Die Stabilitätskorrekturen aus 0.28.4 bleiben enthalten.

**0.28.4 / Android 0.28.4.6:** Stabilitätskorrektur für die Android-STK-Karte: GPS-Netzzuordnung in einem abbrechbaren Hintergrundprozess, zusammengefasste Kartenaktualisierungen und Darstellung von GPS-Linien nur im sichtbaren Ausschnitt. Die große animierte Grafikvorschau wurde entfernt; Zwei-Finger-Zoom bleibt mit kleiner Zoomanzeige erhalten. GPS-Originale und bestätigte Kenntnisse bleiben unverändert.

**0.28.3 / Android 0.28.3.5:** Zwei-Finger-Zoom und Verschieben auf den Android-Karten einschließlich GPS, Demo und Vollbild. Während der Geste erfolgt eine Vorschau, erst beim Loslassen die vollständige Neuzeichnung. Die zweite Streckenkarte wird erst beim Öffnen ihres Reiters aufgebaut; Kartenbewegungen bauen Auswahl- und Bestandslisten nicht erneut auf. Ohne geänderte abgeschlossene Aufzeichnungen wird das vollständige lokale GPS-Archiv nicht bei jedem Wiederholungsversuch erneut eingelesen. Originale GPS-Daten, gespeicherte Kenntnisse und Zoomtasten bleiben erhalten.

**0.28.2 / Android 0.28.2.4:** Die manuelle Streckenkarte nutzt durchgehend 98 % der verfügbaren Breite ohne Rahmen und ohne feste Maximalbreite. Kartenbedienelemente bleiben innerhalb der Karte.

**0.28.1 / Android 0.28.1.3:** „STK-anlegen o. bearbeiten“ mit Knotenauswahl, hellgrünen Standortmarkierungen, hellblauen Vorschlägen verbundener Abschnitte und transparentem Rückgängig-Symbol direkt auf der Karte. Parallele VzG-Abschnitte können gemeinsam ausgewählt, gespeichert und erneut bearbeitet werden; gemeinsame Endpunkte allein reichen nicht aus. Bestehende Auswahlen und Kenntnisse bleiben erhalten.

**Android 0.28.0.2 (Sammelversion):** Android startet mit zuletzt online bestätigtem TF-Konto unmittelbar aus dem lokalen Sitzungsspeicher. DS100/M1 und GPS sind lokal verfügbar; Netzwerkwechsel lösen die erneute Übertragung bestätigter Berichte und vorgemerkter Änderungen aus. Entwürfe werden nicht allein durch eine Wiederverbindung endgültig abgegeben. Die Webversion bleibt 0.28.0.

**0.28.0:** Neue Versionsreihe gemäß Vorgabe: Web 0.28.0 und Android 0.28.0.1. Die vierte Android-Stelle zählt in dieser Reihe ab 1 weiter; der interne Android-versionCode steigt unverändert mit den Workflowläufen.

**0.27.19:** Quellen- und Datenstandhinweise unter der Kenntniskarte sind standardmäßig eingeklappt und lassen sich über ein kleines i-Symbol öffnen und schließen. Die ausführliche CSV-Importanleitung steht ausschließlich in der Hilfe.

**0.27.18:** Die ausführliche Anleitung zur manuellen Streckenkenntnis steht ausschließlich in der Hilfe unter „Streckenkenntnis anlegen“. Der lange Erklärungstext wird auf der Eingabeseite nicht mehr angezeigt.

**0.27.17:** Unter der manuellen Karte steht die aktuelle Punktliste mit DS100, Bahnhof/Meldestelle, Streckennummer und M1-Kilometerangabe. Speichern leert diese Auswahl und übernimmt den Verlauf in eine separate Liste mit Von, Bis und Gültig bis (DD.MM.YYYY). Ein Klick lädt den gespeicherten Verlauf wieder in Karte und Punktliste. Änderungen speichern aktualisiert ihn mit Prüfung auf zwischenzeitliche Änderungen; fremde TF-Bestände bleiben unzugänglich.

**0.27.16:** Rückgängig-Symbol direkt auf der manuellen Karte; dedizierte S-Bahn-Referenzstrecken in Berlin und Hamburg ausgeblendet, parallele Fern-/Güterstrecken bleiben sichtbar. M1-Karten zeigen ab Zoomstufe 11 VzG-Streckennummern in Rot mit schwarzer Kontur auf hellem Hintergrund. Beschriftungen werden je sichtbarer Strecke zusammengefasst und bei Überlappungen oder Platzmangel ausgelassen. Die Betriebsstellen bleiben anklickbar. Gilt für Streckenkenntnisse, manuelle Eingabe, GPS-Aufzeichnung und GPS-Demo.

**0.27.15:** Manuelle Streckenkenntnis fortlaufend über bis zu 1.001 angeklickte Betriebsstellen zeichnen. Der Kartenausschnitt bleibt beim Weiterklicken stehen. Alle vorhandenen importierten, manuellen und GPS-basierten Kenntnisse werden im Editor mit angezeigt; die neue hellgrüne Linie mit heller Kontur liegt darüber.

**0.27.14:** Bahnkarte in GPS-Aufzeichnung und Demo zeigt das offline verfügbare M1-Streckennetz und die M1-Betriebsstellen. Der Reiter Strecken bietet Anzeigen und manuelles Anlegen. Startort per DS100/Name auswählen, automatisch hinzoomen, Betriebsstellen anklicken, VzG-Verbindung prüfen und die hellgrüne Vorschau mit Gültig bis (maximal ein Jahr ab heute) speichern. Manuell bestätigte Strecken gelten als Streckenkundig, ohne GPS-Fahrten zu erfinden. Bestätigte CSV-Importe bleiben führend. Eine lokale Deutschlandkarte bleibt auch ohne Internet im Hintergrund.

**0.27.13:** GPS-Symbole ohne Rahmen in halber Größe; Demo mit Geschwindigkeitsspur und Skala, ohne Geschwindigkeitszahl am Symbol. Neue Verwaltungskachel für TF-Portal-Aufrufe und geprüfte automatische Mitarbeiterpostfächer.

**0.27.12:** Einheitliche Art DB-InfraGo. Das Serverupdate führt bestehende Schreibweisen und doppelte Auswahlwerte in Arbeitsberichten, Entwürfen, Korrekturdaten, GPS-Aufzeichnungen und Demo-Freigaben zusammen. Alte App-Werte bleiben beim Speichern kompatibel. Die Android-App gleicht lokale Berichte und alte GPS-Daten beim Öffnen an. Zeiten, Koordinaten und Revisionsstände bleiben erhalten; PDF-Originale werden nicht neu geschrieben. Zuerst Server, danach App aktualisieren. GPS-Demos zeigen grundsätzlich keine tatsächlichen Geschwindigkeiten oder km/h-Legenden; die Spur wird neutral gefärbt. Freigaben und Kontoeinstellungen können dies nicht einschalten.

**0.27.11:** Synchronisationsfehler öffnen auch einen anderen Arbeitsbericht aus der Monatsliste und dessen fehlerhafte Zeile. Der Dialog nennt Datum, Zugnummer, Uhrzeit und den abgelehnten Wert. Android wertet die Feldzuordnung direkt an der fehlgeschlagenen Anfrage aus; ältere Serverantworten werden mit dem aktuellen Auswahlkatalog abgeglichen. Offene Eingaben im zuvor geöffneten Bericht werden lokal gesichert und beim Wiederöffnen wiederhergestellt. Werte werden nicht automatisch ersetzt.

**0.27.10:** Eingabefehler beim Senden mit Okay gezielt öffnen: Reiter, Zugfahrt und Datenzeile werden eingeblendet, das betroffene Feld wird rot markiert. Veraltete Auswahlwerte und unbekannte DS100-Orte erhalten eindeutige Feldpfade. Offene Bearbeitungen und bereits korrigierte Eingaben bleiben erhalten. Die Updates-Kachel erscheint nur in der Android-App. GPS-Demo-Freigaben werden per Checkbox vorgemerkt und erst mit Auswahl freigeben gemeinsam übernommen. Demo-Standzeiten zeigen nur Uhrzeiten in einer flexiblen Tabelle über die volle Breite.

**0.27.9:** Einzelne abgeschlossene GPS-Aufzeichnungen per Checkbox für andere TF und berechtigte Verwaltungsmitarbeiter freigeben und widerrufen. Gemeinsame GPS-DEMO mit schreibgeschützten Standzeiten und aktuellen DS100-Ortsvorschlägen; Originaldaten bleiben unverändert. TF können die Kachel ausblenden und unter Mein Konto wieder einschalten. Verwaltungszugriff über das Modulrecht GPS-DEMO.

**0.27.8:** Arbeitsberichte mit Schreibrecht zur Überarbeitung an den TF zurückgeben: geschützter Korrekturentwurf, gelbe Monatszeile, Begründung und erneute Synchronisierung als neue Version. Vorherige PDF-Fassung bleibt erhalten; derselbe Arbeitszeiteintrag wird korrigiert und nicht doppelt gebucht. Gesperrte oder zwischenzeitlich geänderte Einträge bleiben geschützt. GPS-Halte nach erkannter Abfahrt schlagen Zugfolge und DB-InfraGo vor. Zwischenstände dürfen Zugfahrten und Details außerhalb der Dienstzeit enthalten; die endgültige Synchronisierung prüft weiterhin die Dienstgrenzen. GPS-Aufzeichnungen werden nicht automatisch gekürzt.

**0.27.7:** Neue TF-Kachel „La-Anweisungen“: PDF-Vorschau und bewusstes Offline-Speichern nach sieben DB-InfraGO-Regionen. Die Verwaltung stellt PDFs mit Ausgabestand und Gültigkeitszeitraum über das Modulrecht „La-Anweisungen“ bereit. Kein automatischer DB-Abruf; vorbereitete Loginfelder und Anmeldebutton sind deaktiviert. Offline-Bestand ist je Konto getrennt und deutlich gekennzeichnet. PDF.js 6.5.438 (Apache-2.0) ist lokal enthalten, damit die Vorschau auch im Android-WebView und ohne externen PDF-Dienst funktioniert.

**0.27.6:** Disponentenverwaltung mit denselben Stammdaten- und Berechtigungsfunktionen wie Verwaltungsmitarbeiter, getrenntem Bestand und standardmäßigem Leserecht für Zugverfolgung. Die Deutschlandkarte zeigt das deutsche Streckennetz und aktiv geteilte GPS-Positionen mit freigegebener Zugnummer und TF-Vornamen; ohne Freigabe und nach zehn Minuten ohne Position bleiben keine Punkte sichtbar. Administratoren finden phpMyAdmin und WebMailer im Administrationsmenü statt als Kacheln. Das angekündigte eigene PNG kann später das vorläufige vorhandene GPS-Symbol ersetzen.

**0.27.5:** Neues Verwaltungsmodul „Strecken- BR- und Ortskenntnisse“: TF über Suche und Dropdown wählen, gemeinsame Karten und Bestände anzeigen, Baureihenkenntnisse anlegen und bearbeiten. Sachbearbeitern das neue Modulrecht „Lesen“ oder „Lesen/Schreiben“ zuweisen. Verwaltungsansichten laden ausschließlich den ausgewählten TF vom Server; private Gerätebestände werden nicht verwendet. Kartenfarben und Legendenbegriffe sind in beiden Portalen vereinheitlicht. Bestätigte importierte Streckenkenntnis bleibt führend.

**0.27.4:** Ortskenntnisse über DS100 eintragen und per Zeilenauswahl bis höchstens ein Kalenderjahr ab heute verlängern. Pro TF keine doppelten Orte. Suche, Spaltensortierung, deutsche Datumsanzeige sowie orange/rote Gültigkeitsmarkierung. Der Import steht unter der Liste. Erfasste GPS-Start-/Endbahnhöfe verlängern den Bestand beim Synchronisieren bis ein Jahr ab ihrem tatsächlichen Erfassungsdatum, ohne längere Gültigkeiten zu verkürzen.

**0.27.3:** Streckenkenntniskarte für große importierte Bestände beschleunigt: zusammengefasste Farbintervalle, zoomabhängige Darstellung und begrenzt zwischengespeicherte Ansichten. Kenntnisse, genaue Abschnittsgrenzen, Importbestätigung und Vorrang vor GPS bleiben erhalten; kein erneuter CSV-Import nötig.

**0.27.2:** Streckenimport unter der Karte mit vorläufiger Kartenansicht und „Import-bestätigen“. Nach dem Speichern ist die Importliste leer, bestätigte Kenntnisse bleiben auf der Karte und haben Vorrang vor GPS. Ortskenntnisse (Bahnhof, DS100, Kundig bis) und Baureihen (Baureihe, Gültig bis) bekommen getrennte TF-bezogene Bestände mit CSV-Import, Vorschau, Bestätigung und Listen.

**0.27.1:** M1-Betriebsstellen für DS100, GPS und Streckenkunde: 42 neue aktive DS100-Einträge, 36 neue eindeutige GPS-Positionen sowie alle 10.632 streckenbezogenen Referenzpunkte. CSV-Import direkt oberhalb der Karte mit automatischer Vorschau nach Dateiauswahl. Importierte Kenntnisse färben die Referenzkarte anhand VzG und DS100 Von/Bis, ohne GPS-Fahrten zu erzeugen; offene Zuordnungen sind sichtbar. [Abgleich und Importregeln](docs/data/M1-BETRIEBSSTELLEN-2026-11-17.md).

**0.27.0:** Web-Version `0.27.0`, Android-Testversion `0.27.0.0`. Weitere Android-Testbuilds zählen die vierte Stelle hoch (`0.27.0.1`, `0.27.0.2`, …). Der interne Android-versionCode steigt unabhängig davon weiter; Updates bleiben über der bestehenden Installation möglich.

**0.26.64:** Doppelt so dicke Linien in der Streckenkenntniskarte. Private Kenntnis-CSV kann im angemeldeten TF-Konto nach Vorschau mit Name und Tf-Nummer importiert werden. Originalstatus, Gültigkeit und Erwerbsangaben bleiben erhalten; keine GPS-Fahrten oder letzten Fahrtdaten werden erzeugt. Wiederholungen erzeugen keine Duplikate, abweichende vorhandene Angaben bleiben erhalten. Persönliche Importlisten sind nach dem Laden auf dem Gerät offline verfügbar.

**0.26.63:** Modulname „Stecken-, BR- und Ortskenntnisse“ mit drei Reitern: Streckenkenntnis, Ortskenntnis und Baureihen. Die bestehende Karte mit Netz, Fahrtenfarben und 180-/365-Tage-Alterung liegt unter Streckenkenntnis. Ortskenntnis und Baureihen zeigen vorerst ausschließlich einen Hinweis auf die späteren Funktionen.

**0.26.62:** Streck-Kenntnisse: unbefahrene Strecken schwarz. Letzte zugeordnete Fahrt bis 180 Kalendertage weiterhin Blau/Grün; ab 181 Tagen Orange, ab 366 Tagen Rot. Grundlage sind die GPS-Zeitstempel je Abschnitt in Europe/Berlin, nicht der Zeitpunkt des Ladens. Legende, Hilfe und DE/PL/EN sind aktualisiert.

**0.26.61:** Bereitgestellte M1-CSV mit 33.425 Datensätzen und 1.549 Streckennummern als einblendbare Referenzebene in Streck-Kenntnisse. Android enthält das Netz auch offline. Befahrene Abschnitte bleiben blau, bis mindestens zwei eigene Zugfahrten je Richtung vorliegen; danach werden sie grün. Die Zuordnung erfolgt konservativ in etwa 100-m-Abschnitten, ohne GPS-Lücken oder mehrdeutige Treffer gutzuschreiben.

**0.26.60:** Excel-Import im Bremszettel-Overlay abgesichert; DU (blau) / DL (rot) als Beta-Anzeige. Android zeigt App-Daten seit Geräteneustart, das Web eine Schätzung pro Tab. GPS pausieren/fortsetzen auch im Vollbild, DB Digi-Bef. beendet das Vollbild vor dem Öffnen. Neue Kachel Streck-Kenntnisse zeigt eigene gemessene GPS-Spuren in Deutschland, ohne Lücken als gefahrene Strecke auszugeben.

**0.26.59:** TF können fehlende DS100-Koordinaten aus einem gemessenen GPS-Punkt ihrer Standzeit bestätigen. Vorschläge werden TF-bezogen offline vorgemerkt und nach aktuellem Serverabgleich global gespeichert. Mehr als 1.000 Meter Abweichung zu einer vorhandenen Position verlangt ein zweites Ja; konkurrierende Änderungen werden vor dem Schreiben erneut geprüft.

**0.26.58:** Die GPS-Bildsymbole zeigen ihren transparenten Hintergrund auch in Karte, Auswahl und Demo. Die helle Hinterlegung in der App-Darstellung wurde entfernt.

**0.26.57:** Original-PNG-Symbole für die GPS-Karte, Auswahl und Demo. GeoPackage-Abgleich ergänzt 1.166 aktive Betriebsstellen, davon 1.042 mit eindeutigen Koordinaten. Der Online-/Offline-Katalog umfasst 14.886 Einträge und 6.450 geprüfte Positionen. Die einmalige Serverergänzung erhält eigene Namen und gelöschte Alteinträge. [Prüfbericht](docs/data/GPKG-DS100-2026-11-15.md).

**0.26.56:** Android enthält den vollständigen DS100-Referenzkatalog mit 13.720 Einträgen und 5.408 geprüften Koordinaten. Standortsuche und Standzeit-Vorbelegung funktionieren offline. Aktuelle Serverkataloge und die häufigen Orte je TF werden lokal gespeichert. Im Browser bleibt die zuvor online geöffnete Seite offline nutzbar.

**0.26.55:** Erkannte GPS-Standzeiten erhalten aus den gespeicherten DS100-Koordinaten einen bearbeitbaren Ortsvorschlag innerhalb von 1.000 Metern. Eigene Ortsangaben bleiben erhalten; unklare Treffer und fehlende Koordinaten werden nicht automatisch zugeordnet.

**0.26.54:** Die GPS-Karte und die Demo zeigen Fahrzeit und Standzeit über dem Symbol ohne Labels als `02:15 / 00:30`. Die Anzeige-Checkboxen steuern weiterhin beide Werte einzeln.

**0.26.53:** GPS-Karte im Vollbild mit Bedienelementen und aktivem Android-Bildschirm. Internationaler Bremszettel als Overlay mit eigenem lokalen Entwurf je Zugfahrt. Deckende Standortauswahl mit bis zu fünf häufigen Orten, Zugfahrtdetails in zwei Zeilen zu je drei Spalten und zehn Tabellenzeilen vor dem Scrollen.

**0.26.52:** GPS-Einstellungen zeigen dieselben kleinen SVG-Symbole wie die GPS-Karte, jeweils mit Radiobutton darunter. Die GPS-Demo lädt die gespeicherten Einstellungen für Symbol, sichtbare Angaben und Standzeitgrenze. Der Demo-Wiedergabestand übernimmt die gewählte Grenze, ohne die Originalaufzeichnung zu verändern. Historische Wiedergabepositionen werden nicht live geteilt; echte Livepositionen werden in der Demo nicht eingeblendet.

**0.26.51:** Mein Konto enthält GPS-Einstellungen für Stopperkennung (1/2/4/5/10/15 Minuten), fünf Punktsymbole und Anzeige-/Freigabefelder. Freigabe ist standardmäßig Nein. Erst ein bewusster Druck auf Teilen während einer laufenden GPS-Aufzeichnung startet die Veröffentlichung einer aktuellen Position, danach höchstens alle fünf Minuten. Angaben erscheinen nur bei beidseitiger Auswahl. Android überträgt aus dem GPS-Hintergrunddienst; keine Nachsendung alter Positionen. Abgelaufene Positionen werden nach zehn Minuten ausgeblendet. Pro TF wird nur die letzte geteilte Position gespeichert. Alte Aufzeichnungen behalten ihre Erkennungsregel.

**0.26.50:** 5.408 eindeutig zuordenbare DS100-Stellen um WGS84-Referenzkoordinaten aus DB-InfraGO-Infrastrukturdaten (Mai 2026) ergänzt. Der normale Serverupdateweg füllt fehlende Positionen in einer eigenen Tabelle; bestehende Positionen, Namen und Codes bleiben erhalten. 857 Kürzel mit abweichenden Namen oder mehreren Referenzpunkten stehen separat zur Prüfung bereit. Keine automatische Zuordnung von GPS-Halten.

**0.26.49:** Wagenmeister haben ein eigenes Verwaltungsmodul mit eigenen Stammdatentabellen und Modulrechten. Personen-, Beschäftigungs- und Adressdaten sowie E-Mail des WGM und Profilbild; keine TF-Nummer, BahnCard, TF-Einsatzart oder Heimatbahnhof. Die bisherige WGM-Kategorie im TF-Modul entfällt. Bestehende WGM-Konten werden unter Erhalt ihrer IDs, Benutzernamen, Passworthashes, Dokumente und Berichte übernommen. Das eigene WGM-Portal folgt später.

**0.26.48:** Neues Verwaltungsmodul Arbeitsberichte für synchronisierte Berichte mit eigenen Zugriffsrechten, Monats-/Mitarbeiter-/Kategoriefilter, Detailansicht und PDF. Die spätere Bearbeitung bleibt offen. Mitarbeiterkategorie WGM (Wagenmeister) auf gemeinsamer Stammdatenbasis ergänzt, unabhängig von der TF-Einsatzart; ein eigenes WGM-Portal folgt später.

**0.26.47:** Der Arbeitsbericht hat drei Reiter im Design der Zugfahrten: Dienstzeit und Gastfahrt, Zugfahrt und Details (GPS), Arbeitsberichte des Monats. Eingaben und laufende GPS-Aufzeichnungen bleiben beim Wechsel erhalten. Neu angelegte oder geöffnete Berichte zeigen Dienstzeit; die Wiederherstellung einer GPS-Aufzeichnung öffnet den GPS-Reiter.

**0.26.46:** Kürzere TF-Kacheln: Doks.-Verwaltung, Meine Bhf's, Mein Konto, Bremszettel Int. und Bremszettel DE. Die neue Kachel Updates zeigt Web-/Android-Version, Updateprüfung, Installation und eine kurze Versionshistorie. Die zusätzliche native Kopfleiste entfällt; Abmelden bleibt im Portal-Header. Im Login erscheint Update nur bei einer heruntergeladenen und geprüften neueren APK. DB Digi-Bef. in der GPS-Ansicht öffnet https://db.de/dibe im externen Browser; der native Android-GPS-Dienst läuft weiter. Optional erhält der aktuelle Halt Art DB InfraGo / Grund DB-Digi-Befehl oder eine manuelle Standzeit beginnt. Der Grund wird einmalig in bestehenden Grundwerten ergänzt und beim Übernehmen in die Zugfahrt erhalten.


**0.26.45:** Der Android-Login zeigt Rail Software mit dem vorhandenen Logo, zentrierten Eingaben und einem abgerundeten Gleisrahmen in Weinrot/Dunkelblau. Hinweis auf das eigene Passwort und das Admin-Passwort zur Erstanmeldung, TF-Nummer, Passwort, Anmelden und der Hinweis zur gespeicherten Anmeldung stehen untereinander. Nach drei abgewiesenen Anmeldungen für dieselbe TF-Nummer erscheint Passwort vergessen mit dem bestehenden Admin-Resetweg; Netzwerkfehler zählen nicht mit. Die App heißt auch im Android-Launcher Rail Software. Bestehende Anmeldungen, Paketname, Signierung und lokale Daten bleiben erhalten.


**0.26.44:** Die GPS-Verfolgungsspur und ihre Legende verwenden wieder 0–140 km/h: 0 blau, 50 grün, 100 gelb, 140 rot, mit fließenden Farbübergängen. Höhere Geschwindigkeiten bleiben rot. Die gemeinsame Skala gilt im Web, in Android und in GPS-DEMO.


**0.26.43 – GPS-DEMO:** Die neue TF-Kachel `/tf/gps-demo` spielt eigene abgeschlossene, synchronisierte GPS-Aufzeichnungen auf der vorhandenen Karte ab. Aufzeichnung nach Zugnummer/Datum auswählen, Laden und Abspielen wählen. Geschwindigkeit: 1×, 5×, 10×, 30×, 60×, 120× oder 300×; fünf Stunden dauern bei 300× eine Minute. Pause, Zeitregler und Zum Anfang steuern die Wiederholung. Die Demo startet keinen Standortdienst und verändert keine GPS-Daten, Standzeiten oder Arbeitsberichte. Zum Laden und für Kartenbilder ist Internet nötig. Server und Android-App aktualisieren.


**0.26.42:** Footer: Rail Software · Version … · Copyright 2026 IO-Software-Görlitz. Das Web zeigt die Serverversion, Android die tatsächlich installierte APK-Version einschließlich Test-Buildnummer.


**0.26.41:** GPS-Lücken erscheinen als direkte hellrosa Verbindung zwischen den genauen Punkten vor und nach dem Ausfall. Die Lückenzeit wird nicht automatisch als Standzeit gewertet. Während einer Lücke kannst Du mit Start Stand / Ende Stand einen manuellen Halt erfassen; er erscheint gelb-rot mit geschätzter Position auf der Verbindung. Vor der Signalrückkehr wird die letzte bekannte Position verwendet. GPS-Rohpunkte bleiben unverändert. Gemessene und manuelle Standzeiten werden in der roten Summe ohne doppelte Zeitanteile addiert. Server und Tablet-App aktualisieren.


**0.26.40:** Die Zugfahrtdetails verwenden zwei gleich breite Bereiche: Art, Grund und Meldestelle/Ort links; Von, Bis und Eintragen rechts. Auf schmalen Bildschirmen stehen die Bereiche untereinander.


GPS-Korrekturen in **0.26.39**: Android lädt die öffentlichen OpenStreetMap-/OpenRailwayMap-Kartenkacheln. Bei Diensten über Mitternacht richtet sich die GPS-Verfügbarkeit nach dem gesamten eingetragenen Dienstzeitraum. Die grüne Anzeige über der Lok zeigt die Gesamtzeit seit Abfahrt einschließlich Zwischenhalten; die rote Anzeige summiert weiterhin die mit GPS erfassten Standzeiten. Internet ist für Kartenbilder erforderlich. Server und signierte Tablet-App aktualisieren.


Anleitungsstand **0.26.38** – Anleitungen und TF-Hilfe für den bestehenden Server, Android-Updates und PDF-Downloads abgeglichen. Server und Tablet haben bereits 0.26.37 installiert. Der bestätigte Android-Ausgangsstand ist `android-test-4` (`0.26.37-test.4`, versionCode `100004`). Neue APKs werden nach erfolgreicher GitHub-Prüfung als eigenes `android-test-…`-Release veröffentlicht.

Für den bestehenden Apache-/MariaDB-Server unter https://ctl-software.io-goerlitz.eu gilt:

```bash
cd /opt/ctlsoftware-test-source &&
git pull --ff-only origin setup/debian-testumgebung &&
sudo bash install-ctlsoftware-test.sh --update --source /opt/ctlsoftware-test-source
```

[Serverupdate und Kontrollen](docs/INSTALL-CTLSOFTWARE-TEST.md#bestehenden-server-aktualisieren). `setup-update.sh`, `setup.sh` und `setup-demo.sh` gehören zu anderen Installationsarten. Die folgenden älteren Funktionsabschnitte beschreiben teilweise diese Varianten; deren Installationsbefehle gelten nicht für diesen Server.

Auf dem Tablet die signierte APK aus den [öffentlichen Test-Releases](https://github.com/omueller369/RailSoftware/releases) verwenden. Die App prüft beim Öffnen/Fortsetzen höchstens alle sechs Stunden; **Update** prüft sofort. Der Download erfolgt automatisch, die Installation nach **Update installieren** und Android-Bestätigung. Vorher offene Eingaben speichern und GPS-Aufzeichnung beenden. Über die bestehende App installieren, damit lokale Daten erhalten bleiben. [Mac, Erstinstallation und bestehender Signierschlüssel](app/docs/ANDROID-STUDIO-TABLET.md).

PDF-Downloads behalten ihren Dateinamen einschließlich UTF-8-Zeichen und `.pdf` sowie den Typ `application/pdf`. In Android im System-Speicherdialog Zielordner wählen und speichern; danach öffnet **Ansehen** eine passende PDF-App. Abbrechen speichert keinen Download.


LokZeitleiste ist jetzt in eine Android-App für Tf und ein Python-Backend für Admins und Monatsdaten geteilt.

## Projektteile

- `app/`: Android-Frontend mit Monatsübersicht, lokaler Erfassung, Zugfahrtbereich aus LokZeit und manuellem Versand des ausgewählten Monats. Die App nutzt ein vom Admin angelegtes Tf-Konto. Sie kann selbst keine Benutzer anlegen.
- `backend/`: FastAPI-Webserver mit MySQL. Admins melden sich unter `/admin` an und legen Tf an. Stammdaten pro Tf: Name, Vorname, Personalnummer, monatliche Sollstunden, Urlaubstage, Geburtsdatum und keine BahnCard, BahnCard 50 oder 100 mit optionalem Gültigkeitsdatum. Monatsdaten und Einträge gehören zu genau einem Tf.
- `docs/` und `design/`: Anforderungen und Tablet-Vorschauen aus den bisherigen Arbeitsschritten.

Die [Gesamtvorschau](design/gesamtvorschau.html) zeigt die früheren Masken. Die [Vorschau für Tagesbeleg und Monatsabrechnung](design/monatsabrechnung-preview.html) zeigt die neuen Masken mit Beispieldaten.

Das Backend enthält jetzt ein Modul für tabellarische PDF-Eingangsbestätigungen mit direktem E-Mail-Versandauftrag und wiederholbarem Versand. E-Mail-Adresse und Bundesland sind Tf-Stammdaten. Eine zweite Backend-Funktion berechnet eine tägliche und monatliche Stundenübersicht mit Gastfahrt, Auffüllung auf acht Stunden nur an Einsatztagen, Urlaub und Krankheit mit jeweils acht Stunden je Tag. Regeln, API-Endpunkte und SMTP-Einrichtung stehen in der [Backend-Anleitung](backend/README.md).

Das [Planungsmodul](backend/lokzeitleiste/planning/README.md) ergänzt administrative Arbeits-, Urlaubs- und Ruhetagspläne pro Tf, Excel-Import mit Vorschau, planbasierte Monatssollstunden und farbige Monats-/Jahres-PDFs.

Die Weboberfläche unter `/admin/planning` bietet einen farbigen Monatskalender mit Tagesbearbeitung, eine Tagesliste für Sammeländerungen, eine Jahresmatrix und Excel-Import.

## Start

Die [automatische Ubuntu-Setup-Routine](setup/README.md) prüft Abhängigkeiten und installiert die vollständige Backend-Testumgebung einschließlich Admin-Konto ohne Rückfragen. Vorprüfung: `bash setup.sh --check`; Installation: `sudo bash setup.sh`. Das zufällige initiale Admin-Passwort steht nur für root lesbar in `/var/lib/lokzeitleiste/admin-initial-password`.

Die [Backend-Anleitung](backend/README.md) beschreibt die Testumgebung auf Ubuntu Server 26.04.1 LTS: Apache läuft auf dem Host, Python-API und MySQL 8.4 in Containern. Im Android-Emulator nutzt ein Debug-Build `-PlokzeitleisteApiBaseUrl=http://192.0.2.10:8080`. Spätere Release-Builds benötigen eine erreichbare HTTPS-Adresse. Die Dienste sind noch nicht auf einem Rechner installiert oder gestartet.

Die App speichert Einträge weiterhin lokal pro Tf. Der Button „Monat senden“ überträgt die Einträge des ausgewählten Monats mit stabilen Kennungen; wiederholtes Senden aktualisiert denselben Datensatz. Einträge werden serverseitig dem angemeldeten Tf zugeordnet. Die Zugfahrt-Standzeiten aus LokZeit bleiben zunächst lokal und sind noch nicht mit den Monatsdaten verbunden.

## Noch offen

- Apache, MySQL und Python-API müssen auf dem vorgesehenen lokalen Rechner installiert und gestartet werden. Für ein physisches Tablet wird später eine erreichbare HTTPS-Adresse benötigt.
- Es gibt noch keinen vollständigen Abgleich zwischen App und Server: lokale Löschungen werden nicht übertragen, Serverdaten nicht automatisch abgerufen, parallele Geräte nicht zusammengeführt.
- Die achtstündige Höchstgrenze für Bereitschaft ist weiterhin eine vorläufige Annahme. Rufbereitschaft ist auf 08:00–20:00 Uhr und höchstens acht Stunden beschränkt.
- Berechnung von Arbeits-, Nacht- und Sonntagsstunden und später Ausbleibe benötigt noch verbindliche Fachregeln. Die bisherigen vorläufigen Regeln stehen in der App und in den früheren Anforderungen.
- Nach 365 Tagen läuft das Anmeldetoken ab. Danach ist eine neue Anmeldung nötig. Ein vollständiges Migrationstool für spätere Änderungen an bestehenden Tabellen steht noch aus.

Der Python-API-Testlauf wurde lokal mit SQLite als isolierter Testdatenbank geprüft. Ein MySQL-Integrationslauf und ein Android-Build waren in dieser Umgebung ohne MySQL-Server bzw. Android SDK nicht möglich. Die Android-Layouts wurden für schmale Ansichten angepasst; ein Build und Gerätetest stehen noch aus.

## Arbeitszeitkorrekturen

Administratoren können Arbeitsbeginn und Arbeitsende je Mitarbeiter unter `/admin/worktime` bearbeiten. Tages-, Wochen- und Monatswerte werden neu berechnet; jede tatsächliche Änderung erzeugt eine E-Mail mit Vorher-/Nachher-Werten und einen nachvollziehbaren Änderungsverlauf. [Bedienung, Versand und Update](backend/lokzeitleiste/worktime/README.md). In der Testumgebung landen Benachrichtigungen in Mailpit.

## Verwaltungsmitarbeiter und Passwörter

Unter `/admin/staff` Verwaltungsmitarbeiter mit Stammdaten, mehreren Adressen und Modulrechten anlegen. Neue Konten müssen beim ersten Login ihr Initialpasswort ändern. Mitarbeiter und Administratoren ändern ihr eigenes Passwort unter `/account`; Administratoren können Initialpasswörter zurücksetzen. [Berechtigungen und Bedienung](backend/lokzeitleiste/accounts/README.md). Die Android-App ab Version 0.7 unterstützt Erstlogin und eigenen Passwortwechsel.

## Zeiterfassung, mobile Ansichten und Fotos

Tf und Verwaltungsmitarbeiter erfassen eigene Zeiten unter `/my/worktime`; die Verwaltung kann im Arbeitszeitmodul Einträge erfassen, bearbeiten und sperren. Entsperren erfordert die Modulstufe Administration. [Bedienung und API](backend/lokzeitleiste/records/README.md). Tf-Anlage (`/admin/tf/new`) und Tf-Übersicht (`/admin/tf`) haben getrennte Menüpunkte. Beide Mitarbeitermodule bieten geschützte Foto-Uploads.

Die Planung unterstützt Mehrfachauswahl in Kalender, Tagesliste, Jahresmatrix und Excel-Vorschau. Auswahl und ungespeicherte Änderungen bleiben innerhalb desselben Jahres erhalten; Änderungen über Monatsgrenzen werden gemeinsam gespeichert. Webansichten sind für kleine Bildschirme angepasst, breite Tabellen scrollen innerhalb ihres Bereichs. Android 0.8 ergänzt mobile Layoutanpassungen. Praktische Tests auf Mobilgeräten stehen noch aus.

Die Arbeitszeitplanung verwendet jetzt automatisch die gesetzlichen Berliner Feiertage. Diese werden mit Namen und eigener Farbe angezeigt und haben immer 0 Sollstunden, auch bei eingetragenem Arbeitstag oder Urlaub. Dies gilt für Webansichten, Monatssaldo, PDF und Excel.

## Erweiterungen v0.18

Feiertage mit geplanter Arbeit, Urlaub oder Ruhe zeigen Feiertagsfarbe und Statusfarbe diagonal in Webansichten, PDF und Excel. Das Feiertags-Soll bleibt 0 h. Fotos können direkt beim Anlegen und Bearbeiten von Tf und Verwaltungsmitarbeitern ausgewählt und mit dem Profil gespeichert werden. Tf-Stammdaten besitzen jetzt einen vollständigen Bearbeitungsdialog.

Die Zeiterfassung und Zeitkorrektur haben ein eigenes Enddatum. Neue Erfassungen beginnen mit gleichem Beginn-/Enddatum; für Schichten über Mitternacht einen späteren Tag wählen. Tages-, Wochen- und Monatswerte berücksichtigen den tatsächlichen Zeitraum. Android 0.10 ergänzt Enddatumsauswahl, Speicherung und monatsbezogene Aufteilung. Ein Android-Build und Tests auf echten Geräten stehen noch aus.

Tf-Stundenübersicht: In der Tf-Liste „Stundenübersicht“ wählen. Tagesdetails, Monatskalender und Jahreskalender vergleichen geleistete Arbeitszeit (inklusive Gastfahrt, ohne Pausen) mit dem Plansoll. Die separate Gutschrift enthält Auffüllung, Urlaub und Krankheit. Farben und diagonale Berliner Feiertagsmarkierungen entsprechen der Arbeitszeitplanung. Offene Planung wird als vorläufig markiert und erhält keinen abschließenden Saldo. Lesefreigaben für Planung und zusätzlich Arbeitszeit oder Berichte sind erforderlich. API: `GET /api/v1/admin/tf/{tf_id}/hours/{year}`. Keine Datenbankmigration erforderlich.

## Backend-Menü ab Version 0.18

1. Administration (Gruppentitel ohne Modulaufruf)
   - 1.1 Verwaltung: gemeinsame Übersicht aller VM und Tf mit Suche und Filter
   - 1.2 VM (Verwaltungsmitarbeiter) anlegen
   - 1.3 TF (Triebfahrzeugführer) anlegen
2. Personalplanung
   - 2.1 Personalplanung TF Übersicht
   - 2.2 Schichtplan: Modelle und Zeitraumzuweisung
3. Triebfahrzeugführer
   - 3.1 Dienstplan: Monatsansicht der Planung ohne Bearbeitung
   - 3.2 Dienstzeit: Stundenübersicht mit Monatswahl sowie Tag/Jahr
   - 3.3 Email: Tf-Postfächer
4. Sonstiges (Platzhalter ohne Funktion)
5. Abmelden

Das Menü erscheint auf allen Backend-Modulseiten und berücksichtigt die Freigaben. Bestehende Stammdaten-, Passwort- und Arbeitszeitkorrekturansichten bleiben als ergänzende Links verfügbar. Neue Checkboxmodule sind „Verwaltung: alle Mitarbeiter“, „Schichtmodelle und Zuweisungen“ und „Tf-E-Mail-Postfächer“. Administratoren erhalten alle Rechte; bestehende Verwaltungsmitarbeiter müssen für neue Module ausdrücklich freigeschaltet werden.

[Schichtmodelle und Zuweisungen](backend/lokzeitleiste/planning/SHIFTS.md) · [Postfach-Einrichtung](backend/lokzeitleiste/mailbox/README.md) · [Mehrsprachigkeit](backend/lokzeitleiste/locales/README.md)

Portal, Backend und Android-App unterstützen Deutsch (Standard), Polnisch und Englisch. Die Sprachauswahl im Seitenkopf bleibt lokal und nach Anmeldung im jeweiligen Konto gespeichert. Texte werden über stabile Schlüssel und eigene Sprachdateien je Modul gepflegt: `backend/lokzeitleiste/locales/modules/<modul>/{de,pl,en}.json`. Nach Änderungen `python tools/build-translations.py` ausführen; `--check` prüft die erzeugten Browser-, Backend- und Android-Kataloge. Hilfesuche und Hilfedruck verwenden die gewählte Sprache. Persönliche Texte und gespeicherte Fachwerte bleiben unverändert. Die Android-App anschließend neu bauen und installieren.

Update der bestehenden Standalone-Installation: den oben genannten Updatebefehl mit `install-ctlsoftware-test.sh --update --source` verwenden. Die neuen Tabellen für Modelle, Zuweisungen, Postfächer, Entwürfe und Kontosprachen werden automatisch angelegt; bestehende Spalten bleiben erhalten. Für E-Mail-Postfächer die privaten `MAILBOX_*`-Werte ergänzen. Die reale IMAP-/SMTP-Verbindung, MySQL-Integration und der Android-Build müssen auf der Zielumgebung geprüft werden.

## Erweiterungen v0.19

TF und Verwaltungsmitarbeiter werden in Tabellen mit Links für Ansicht und Bearbeitung angezeigt. Foto-Upload ist auf Anlage und Bearbeitung begrenzt; die Ansicht bleibt schreibgeschützt. Passwortzurücksetzen ist in der Bearbeitung erreichbar.

E-Mail-Konten erhalten pro TF gespeicherte, änderbare Anbieter- und Servereinstellungen: Googlemail, Apple/iCloud, WEB.DE, Yahoo, Microsoft sowie manuelle IMAP-/SMTP-Server. Microsoft verwendet OAuth2 mit Gerätecode und Token-Erneuerung. Die Registrierung einer Microsoft-App und die private Konfiguration ihrer Client-ID sind erforderlich. Details: [Postfach-Einrichtung](backend/lokzeitleiste/mailbox/README.md).

Bestehende globale Mailserverangaben bleiben für bisherige Konten gültig, bis eigene Serverangaben gespeichert werden. Neue Tabellen werden beim Start über das bestehende Datenbankschema-Setup angelegt; vorhandene Konten werden nicht gelöscht. Anbieter-Verbindungen und Microsoft-App-Freigaben wurden mit simulierten Antworten geprüft; echte Konten müssen auf dem Zielserver eingerichtet und getestet werden.

## Erweiterungen v0.20 – Grenzdienst Polen

TF werden beim Anlegen und Bearbeiten als Strecken-TF, Grenz-TF oder beides geführt. Die TF-Tabelle zeigt den Typ und kann danach gefiltert werden (Grenz-/Streckenfilter schließen „beides“ ein). Bestehende Konten gelten zunächst als Strecken-TF.

Schichtmodellblöcke und Tagespläne unterscheiden Streckendienst (8 h), Grenzdienst Tag (09:00–21:00, 12 h) und Grenzdienst Nacht (21:00–09:00 am Folgetag, 12 h). Grenzschichten dürfen Grenz-TF und beiden Typen zugewiesen werden. Urlaub bleibt 8 h, Ruhe 0 h, Berliner gesetzliche Feiertage 0 h Soll. Die vollständige Nachtschicht wird im Plan dem Startdatum zugeordnet, auch bei Monats-/Jahreswechsel. Die Uhrzeiten sind lokale Planzeiten; das feste Plansoll beträgt auch bei Zeitumstellung 12 h. Tatsächliche Arbeitszeiterfassungen bleiben getrennt und werden nicht automatisch aus dem Plan erzeugt.

Die Tages-, Monats- und Jahressummen sowie Dienstzeitübersicht, PDF und Excel verwenden die gespeicherte Schicht. Manuelle neue Arbeitstage ohne Schichtangabe erhalten für reine Grenz-TF die Tagschicht; für Strecken-TF und „beides“ Streckendienst. Schichtmodelle wählen den Dienst ausdrücklich. Bestehende Modelle bleiben Streckendienst. Vorhandene Tagespläne ändern sich durch die bloße Änderung des TF-Typs nicht rückwirkend. Schichtwechsel werden mit Revision und Vorher-/Nachher-Werten protokolliert.

Excel: Die bisherigen vier Spalten bleiben gültig. Eine optionale fünfte Spalte `Schicht` verwendet `standard`, `border_day` oder `border_night`. Vorlagen exportieren diese Spalte, damit Grenzschichten beim erneuten Import erhalten bleiben. Ohne Schichtangabe bleiben bestehende Arbeitstag-Schichten erhalten; bei neuen Tagen gilt die obige Standardregel.

Die Grenzdienst-Schichtfolge (Anzahl Tag-, Nacht- und Ruhetage) ist im Schichtmodell frei einzustellen; eine betriebliche Folge ist noch nicht vorgegeben. Pausen werden weiterhin in der tatsächlichen Zeiterfassung eingegeben; 12 h bezeichnet hier das Plansoll für den genannten Dienstzeitraum.

Googlemail: Button „Mit Google verbinden“ mit OAuth2/API-Kontoanbindung, automatischer Adressübernahme und Token-Erneuerung. Auf dem Server müssen Google-Client-ID, Client-Secret und öffentliche HTTPS-Adresse einmalig eingerichtet sein. iCloud: Button mit vereinfachtem Dialog (Adresse + Apple-App-Passwort), automatische Serverwerte; keine öffentliche Apple-Mail-OAuth-API für diese eigene Anwendung integriert. Details und Einrichtung im [Postfach-Handbuch](backend/lokzeitleiste/mailbox/README.md).

## BahnCard im TF-Profil

Beim Anlegen, Bearbeiten und Ansehen stehen „Keine BahnCard“, „BahnCard 50“ und „BahnCard 100“ zur Verfügung. Für BahnCard 50/100 wird „Gültig bis“ als Datumsfeld eingeblendet. Das Datum ist optional, damit bestehende Profile ohne bekanntes Ablaufdatum weiter bearbeitet werden können. Bei „Keine BahnCard“ wird das gespeicherte Datum gelöscht. Ältere API-Clients erhalten beim unveränderten Kartentyp ein bereits hinterlegtes Datum.

Die neue Zusatztabelle `tf_bahncard_validity` wird durch den bestehenden Datenbankinitialisierungsschritt angelegt; vorhandene TF-Tabellen benötigen keine Spaltenänderung.

## TF-Stammdaten v0.22

TF-Nummer: eindeutige sechsstellige Ganzzahl (100000–999999), zugleich Loginname für Backend und Android-App. Beim nächsten Containerstart legt `init_db` die neuen Zusatztabellen an und stellt bestehende TF einmalig auf zufällige freie Nummern 787000–787999 um. Verwaltungs- und Administratorkonten bleiben erhalten. Es sind maximal 1000 Nummern mit diesem Präfix verfügbar; bei ausgeschöpftem Bereich bricht die Migration ohne Teiländerung ab. Die Zuordnung alter/neuer Namen wird intern in `tf_number_migrations` dokumentiert. Bestehende TF-Sitzungen werden beendet; Passwörter und serverseitige Stunden-/Plandaten bleiben ihren unveränderten Benutzer-IDs zugeordnet. Die Android-App übernimmt beim ersten verifizierten Login lokale Daten unter dem bisherigen Namen.

Die neuen Formulare erfassen Beitrittsdatum, Staatsangehörigkeit (249 ISO-Länder/Gebiete), Wochenarbeitszeit, eine bis zehn Adressen mit Bundesland sowie optional einen Heimatbahnhof. Bei mehreren Adressen muss genau eine Postanschrift markiert sein. Die einzige Adresse gilt automatisch als Postanschrift. Beim Löschen der Postanschrift bietet der Dialog Abbrechen oder die vollständige Eingabe einer Ersatzadresse an. Das Bundesland der Postanschrift wird für personenbezogene Arbeitszeitberichte übernommen; die Personalplanung verwendet weiterhin Berlin.

Ein Austrittsdatum sperrt ab 00:00 Uhr dieses Tages in Europe/Berlin. „Sofortige Sperre“ wirkt unabhängig von einem zukünftigen Austritt. Jede authentifizierte Serveranfrage prüft beide Sperren, auch bei bereits ausgegebenen Tokens. Die App prüft den Kontozugang bei geöffnetem Bildschirm alle 30 Sekunden; ohne Netz kann sie eine neue Serversperre nicht erkennen, sämtliche Serveroperationen bleiben serverseitig geschützt. Eintritt/Austritt verändern keine historischen Zeitdaten.

Wochenarbeitszeit ersetzt die freie Monatssoll-Eingabe. Vertragliche Monatssollstunden = Wochenminuten / fünf (auf volle Minuten gerundet) × Montag–Freitag ohne Berliner Feiertage im jeweiligen Monat. Die Vorschau zeigt den aktuellen Monat. Der individuelle Plan berechnet Standard-Arbeitstage aus Wochenminuten / fünf, Grenzschichten mit 12 Stunden, Urlaub mit acht Stunden, Ruhetage und Feiertage mit null. Plan-Soll und vertragliches Kalender-Soll werden separat als `target_minutes` und `contract_monthly_minutes` geliefert. Alte Monatswerte werden mit 12/52 in Wochenwerte überführt und auf mindestens 40 Stunden korrigiert (maximal 168 Stunden); neue Eingaben erlauben auch Teilzeit.

Bei BahnCard 50/100 erscheint „Gültig bis“ sofort. Standardwert: heutiger Berliner Kalendertag plus 365 Tage; das Feld kann optional geleert werden. Vorhandene Daten werden übernommen.

Die DS100-Suche verwendet eine lokale Datenbank und sucht nach Kürzel oder Name. Datenstand, Lizenz und Import der aktuellen offiziellen DB-InfraGO-Datei stehen in [STATION_SOURCES.md](backend/lokzeitleiste/accounts/STATION_SOURCES.md). Die enthaltene offene Liste hat Stand 04/2018 und wird im Formular entsprechend gekennzeichnet.

Nach Aktualisierung des Branches müssen die Servercontainer neu gebaut und gestartet werden, damit `init_db` die Migration ausführt. Vorher ein Datenbankbackup erstellen. Die Änderungen wurden in einer isolierten SQLite-Testumgebung geprüft; eine bestehende externe Serverdatenbank wurde hier nicht verändert. Ein Android-Build erfordert weiterhin das Android SDK.

## TF-Testdaten v0.23

Das Geschlechtsfeld bietet „Männlich“, „Weiblich“, „Divers“ und „Keine Angabe“ beim Anlegen, Bearbeiten und Ansehen. Bestehende Profile ohne Angaben werden als „Keine Angabe“ angezeigt. Die neue Tabelle `tf_identity` wird vom regulären Datenbankinitialisierungsschritt angelegt.

Eine ausdrücklich aufrufbare [Testdatenroutine](backend/lokzeitleiste/accounts/demo_tf/README.md) ersetzt alle TF einschließlich abhängiger Daten durch 20 fiktive Personen mit individuellen KI-Profilbildern. Die Routine erzeugt die gewünschten Geschlechts-/TF-Typen und BahnCard-Verteilungen, 40 Wochenstunden, 30 Urlaubstage, 787xxx-Logins, fünfstellige Personalnummern, fiktive Adressen und die gemeinsame E-Mail-Adresse. Initialpasswort: `[eigenes sicheres Passwort]`, anschließend verpflichtender Passwortwechsel. Die Ablaufdaten der BahnCards werden relativ zum Ausführungstag gewählt.

Die tatsächliche Serverdatenbank wird erst durch `bash backend/testenv/control.sh demo-tf` zurückgesetzt. Normale Starts/Updates löschen keine TF. Ausführung, Sicherung, Verteilung und Bildprompts sind in der Anleitung dokumentiert.

## TF Portal v0.24

Nach dem TF-Login öffnet sich `/tf`: Arbeitsbericht, Lokübergabebuch und Leuna Übergabeprotokoll sind zunächst eigene Platzhalterseiten. Arbeitsplan (`/tf/arbeitsplan`) zeigt den eigenen aktuellen Monatsplan aus der Personalplanung, mit Monatswechsel, Schichtbeginn/-ende (einschließlich Folgetag), Sollstunden, Notizen und diagonal gefärbten Feiertags-/Statusmarkierungen. TF können diesen Plan nur lesen. Die Anzeige ist mobil nutzbar und in Deutsch, Polnisch und Englisch übersetzt. Eigene Arbeitszeiterfassung und Passwortwechsel bleiben erreichbar.

Passwörter können ab v0.24 sechs Zeichen lang sein: TF-/Verwaltungskontoanlage, Administrator-Bootstrap, Passwortwechsel und administrativer Reset verwenden mindestens sechs Zeichen. Der verpflichtende Erstwechsel und das Beenden alter Sitzungen bei Passwortänderungen bleiben erhalten. Bestehende Passwortprüfwerte bleiben gültig. Die Android-Passwortwechselmaske akzeptiert ebenfalls sechs Zeichen; das neue TF Portal ist die Weboberfläche.

## Arbeitsbericht v0.25

Im [TF Portal](backend/lokzeitleiste/work_reports/README.md) Dienstbeginn/-ende, sofortige Dienstzeit-/Pausenberechnung, Pflichtbegründung bei mehr als zwölf Stunden, mehrere DS100-Gastfahrten, Beleg-Upload und die Monatsübersicht nutzen. Synchronisierte Berichte fließen einmalig in die bestehende Arbeitszeitberechnung ein. Belege werden nach dem Speichern über eine dauerhafte Warteschlange versendet; `WORK_REPORT_RECEIPT_EMAIL` konfiguriert das Ziel in API und Mailer. Der Teststack verwendet admin@example.org` und fängt Nachrichten in Mailpit ab. Details zu Pausen, Originaldaten, lokalen Entwürfen, Dateigrenzen und Versand stehen in der Modulbeschreibung.

## Persönliche Menüvariante

Unter **Startseite → Menü anpassen** kann jeder Backend-Benutzer seine Navigation wählen und mit **Menüvariante speichern** dauerhaft im eigenen Benutzerkonto speichern. Der Menüpunkt **Menü anpassen** bleibt in allen Varianten erreichbar. Die Auswahl lässt sich jederzeit ändern und gilt nach erneutem Login auch auf anderen Geräten. Modulberechtigungen bleiben bestehen.

- **Seitenleiste** (Voreinstellung): links am Desktop, aufklappbares Seitenmenü auf Mobilgeräten.
- **Menü oben rechts**: kompaktes Menü mit mehr Platz für die Arbeitsfläche.
- **Hauptbereiche + Kacheln**: Bereichsleiste am Desktop und unten auf Mobilgeräten; „Mehr“ öffnet den vollständigen Menübaum.

Beim regulären Update bzw. bei der Neuinstallation wird die Tabelle `backend_menu_preferences` automatisch angelegt. Bestehende Benutzer starten ohne Datenmigration mit der Seitenleiste. Die Auswahl benötigt keine zusätzliche Modulfreigabe. TF verwenden weiterhin das TF-Portal.

## Android TF-Portal 0.11

Die Android-App übernimmt den aktuellen TF-Portalstand als gemeinsam gebündelte Oberfläche, ergänzt um native Dateiauswahl, Downloads und einen GPS-Standortdienst für die Bildschirmsperre. Die bisherige native Erfassung bleibt erreichbar. [Funktionen, Offline-Verhalten, Build und Installation](app/docs/TF-PORTAL.md). Eine aktualisierte Serverinstallation und eine neu gebaute APK sind erforderlich.

Die [Schritt-für-Schritt-Anleitung für Android Studio, Tabletinstallation und GitHub-Updates](app/docs/ANDROID-STUDIO-TABLET.md) beschreibt insbesondere den dauerhaft identischen Signierschlüssel und die vier notwendigen Repository-Secrets. Die App prüft beim Öffnen/Fortsetzen automatisch auf signierte Test-Releases; Android verlangt weiterhin eine Installationsbestätigung.

## Lokübergabebuch im Web-Backend

Unter **Sonstiges → Lokübergabebuch** steht die Fahrzeugübersicht mit denselben drei Spalten wie in der Fahrzeugverwaltung bereit: farbiger Statuskreis, Fahrzeugnummer und Name. Die Statuslegende folgt unter der Tabelle; Suche und Statusfilter nutzen dieselben aktuellen Stammdaten. Das Modul ist auf der berechtigten Startseite verfügbar. Verwaltungsmitarbeiter benötigen die neue Modulfreigabe **Lokübergabebuch → Lesen**; Administratoren haben Zugriff. Der erste Ausbauschritt ist eine Übersicht, ohne neue Fahrzeugstammdaten oder Übergabeeinträge anzulegen.

Bei Auswahl einer Lok im Lokübergabebuch öffnet sich eine Textansicht mit Statustext und passender Hintergrundfarbe, Grund/Einschränkung bei gelbem oder rotem Status, Name, vollständiger Fahrzeugnummer und Baureihe. Die Schaltfläche „Übergabeprotokoll“ öffnet die Protokollerfassung; „PZB“ und „Störungen“ sind noch Platzhalter. Die Ansicht verwendet die Modulfreigabe des Lokübergabebuchs, ohne eine zusätzliche Fahrzeugstammdaten-Freigabe zu verlangen.

## Grundwerte für die Lokübergabe

Unter **Sonstiges → Stammdaten → App Grundwerte → Lokübergabe** lassen sich Meldungsempfänger mit Name und Emailadresse, PZB-Gründe (maximal 255 Zeichen) und Störungskategorien (maximal 100 Zeichen) anlegen und bearbeiten. Empfänger stehen in einer Tabelle unter der Eingabe, PZB-Gründe und Kategorien in Auswahllisten; eine Auswahl lädt den Eintrag zur Bearbeitung. „Neu“ startet eine weitere Eingabe.

Jede Störungskategorie kann einen Hotline-Namen und eine Hotline-Emailadresse erhalten. Sobald Kategorien existieren, erscheint darunter die Eingabe „Eingrenzung der Schadstelle“. Zuerst eine Kategorie auswählen, dann deren Schadstellen anlegen oder aus der zugehörigen Listbox zur Bearbeitung laden. Gleiche Schadstellenbezeichnungen sind in verschiedenen Kategorien möglich. Gleichzeitig bearbeitete, veraltete Datensätze werden beim Speichern zurückgewiesen.

Die bestehenden Modulrechte **App Grundwerte** gelten auch hier: Lesen für die Anzeige, Lesen und Schreiben zum Anlegen und Bearbeiten. Die Daten bleiben getrennt von den bisherigen Gründen/Arten der Zugfahrten. Beim regulären Setup/Update legt `init_db` die neue Tabelle `loco_handover_defaults` automatisch an; vorhandene Grundwerte bleiben erhalten. Diese Erweiterung versendet keine Emails; sie bereitet die späteren Lokübergabeformulare vor.

Im **TF-Portal → Lokübergabebuch** öffnet die Kachel direkt `/tf/loco-handover` mit derselben Fahrzeugliste und Detailansicht. Der bisherige Link `/tf/lokuebergabebuch` bleibt gültig. Das Modul ist aus der Platzhalter-Zuordnung des Portals entfernt; die Portal-Einstiegsseiten und das Portal-Script verwenden `Cache-Control: no-store`. Nach dem Update der bestehenden Standalone-Installation mit dem oben genannten Updatebefehl das TF-Portal vollständig neu laden. Ein reines `git pull` ersetzt das laufende Backend nicht. In der Android-App erfordert die geänderte gebündelte Oberfläche zusätzlich eine neue APK.


## Fahrzeugbezogene Übergabeprotokolle

Im Lokübergabebuch öffnet „Übergabeprotokoll“ die Eingabemaske zur ausgewählten Lok. Erfasst werden Datum/Uhrzeit (Berliner Ortszeit, Anzeige `TT.MM.JJJJ HH.MM`), V/A-Dienst, eine bis zu sechsstellige ganzzahlige Zugnummer, Betriebsstelle über DS100-/Namenssuche, Besonderheiten mit Zeichenzähler (1000 Zeichen), Meldungsempfänger aus App Grundwerte, Zähler 1.8.0 und 2.8.0 sowie Kilometerstand (jeweils höchstens acht Ziffern). Führende Nullen bleiben erhalten. „Eintragen“ speichert und schließt, „Abbrechen“ schließt ohne Speicherung.

Die Protokolle sind dem **Fahrzeug** zugeordnet und für **alle angemeldeten aktiven TF** sichtbar – einschließlich Details und Anhängen. Die Tabelle zeigt getrennte Spalten für Datum und Uhrzeit, danach V/A-Dienst, Namen des Erfassers, Zugnummer, Betriebsstelle und Besonderheit; ein Klick öffnet sämtliche Details. Namen, Fahrzeugstatus, Betriebsstelle und Meldungsempfänger werden als historischer Stand gespeichert. Die TF-Nummer wird nicht veröffentlicht. Verwaltungspersonal benötigt zum Erfassen „Lokübergabebuch → Lesen und Schreiben“, zum Anzeigen genügt Lesen.

Mehrere PDF-, JPEG- oder PNG-Anhänge sind möglich: höchstens zehn Dateien, jeweils maximal 10 MB, zusammen maximal 30 MB. Protokoll und Anhänge werden gemeinsam gespeichert; fehlerhafte Dateien erzeugen keinen unvollständigen Datensatz. Downloads erfordern dieselbe Anmeldung wie das Lokübergabebuch. Die Empfängerauswahl wird dokumentiert; ein Emailversand ist in diesem Ausbauschritt nicht eingerichtet. Beim Setup/Update legt `init_db` die Tabellen `loco_handover_protocols` und `loco_handover_attachments` automatisch an.


Die Checkbox **Lokdaten** direkt neben dem Datei-Upload kennzeichnet, dass die angehängten Dateien Energiewerte und Kilometerstand enthalten. Der Wert wird mit dem Protokoll gespeichert und in dessen Detailansicht angezeigt; ältere Protokolle gelten ohne Kennzeichnung.

Neue Anhänge werden in 256-KiB-Abschnitten in `loco_handover_attachment_chunks` gespeichert, damit ein erlaubter Anhang unter 10 MB keine entsprechend große einzelne MySQL-Anweisung benötigt. Die beim Update automatisch angelegte Zusatztabelle ändert nichts an vorhandenen Anhängen: diese bleiben unverändert lesbar. Protokoll und Dateiabschnitte werden weiterhin gemeinsam transaktional gespeichert. Fehler werden direkt neben dem Upload angezeigt, auch bei nicht als JSON gelieferten Serverfehlern oder einer unterbrochenen Verbindung. Der Onlineserver muss für diese Änderung regulär aktualisiert werden.

Hochgeladene JPEG- und PNG-Bilder erscheinen in den Protokolldetails direkt als responsive Bilder mit Dateinamen. Andere Dokumente bleiben Downloadlinks. Die Bildvorschau erfordert dieselbe Anmeldung wie der Dateidownload und ist auch für bisher gespeicherte Bilder verfügbar.

## Neuinstallation auf vorhandenem Ubuntu mit ISPConfig

`sudo bash setup-ispconfig.sh` installiert ausschließlich die Anwendung mit ihren Python-Abhängigkeiten, eigenen systemd-Diensten und den 20 Test-TF samt Bildern. Sie nutzt eine bereits in ISPConfig angelegte Website und eine leere Datenbank. Es werden keine Web-/Datenbank-/Mailserver, Docker oder ISPConfig installiert und keine fremden VirtualHosts verändert. [Vollständige Anleitung mit Prüf- und Installationsbefehlen, HTTP/HTTPS, Apache/nginx und Testzugängen](docs/SETUP-ISPCONFIG.md).

## Interaktive Installation mit einer Datei

**`install-ctl-software.sh`** enthält die vollständige Setup-Logik für eine vorhandene ISPConfig-Subdomain. Es fragt Subdomain, MariaDB-Datenbank und -Benutzer sowie verdeckt das Passwort ab; fehlendes Python, venv, Git und weitere Anwendungswerkzeuge werden mit sudo nachinstalliert. Der bestehende Web-/Datenbank-/ISPConfig-Stack wird weiterverwendet. Die 20 Test-TF inklusive Bildern sind enthalten. [Download, Aufruf und verbleibende ISPConfig-Weiterleitung](docs/INSTALL-CTL-SOFTWARE.md).

## Vollständiger neuer Ubuntu-26.04-Testserver

**`install-ctlsoftware-test.sh`** richtet auf einem frischen Ubuntu 26.04 die gesamte Serverumgebung ein: Apache/HTTPS, MariaDB (`db_ctl`/`dbo_ctl`, Passwort wird abgefragt), DNS-Vorgaben für STRATO (BIND nur lokal), Postfix/Dovecot, DKIM/SRS und die CTL-Anwendung mit 20 Test-TF samt Bildern. Domain `portal.example.org`, IP `192.0.2.10`. Die vier Postfächer `info`, `diso`, `vkplanung` und `railpool` speichern Nachrichten lokal und leiten sie zusätzlich an admin@example.org` weiter. [Vollständige Anleitung, DNS-Voraussetzungen, Mailzugänge und Fortsetzung](docs/INSTALL-CTLSOFTWARE-TEST.md). Dies ist eine eigene Installationsart ohne ISPConfig und kein Update der bisherigen laufenden Umgebung.

Persönliche TF-/Mitarbeiterpostfächer, Domainliste und Update einer bestehenden Standalone-Testinstallation: [Anleitung](docs/EMPLOYEE-MAIL-UPDATE.md).


## Arbeitsbericht und GPS v0.26

Diese Version basiert auf dem Stand 0.25 des Branchs `setup/debian-testumgebung`, nicht auf der RC1. Der GPS-Ablauf wurde auf manuelle Start-/Endbahnhöfe und eine lokale Live-Standzeitenliste umgestellt. Die vollständige Bedienhilfe einschließlich Wiederherstellung, Zwischenspeichern und Löschen steht unter [Version 0.26](docs/VERSION-0.26.md) und im Hilfe-Button des Arbeitsberichts/GPS-Bereichs.


## Anleitung und Hilfe im TF-Portal

Das Modul `/tf/hilfe` und die Schaltfläche `? Hilfe` verwenden den gemeinsamen, nach Modulen und Themen gegliederten Katalog in `backend/lokzeitleiste/static/tf-help-content.js`. `tf-help.js` zeigt Suche, Kurztexte und das Hilfefenster mit X links und Drucker rechts. Die Druckansicht enthält ausschließlich die ausgewählte Anleitung, keine persönlichen Formulare. Android verwendet dafür einen eigenen System-Druckdialog mit einem getrennten, netzwerkgesperrten Druck-WebView.

Die Hilfepflege gehört zu jeder Änderung der TF-Bedienung; siehe [AGENTS.md](AGENTS.md). Die Modulabdeckung wird automatisch geprüft.


### Persönliche TF-Notizen und Du-Anrede

Im TF-Portal ergänzt das Modul **Notizen** persönliche, serverseitig zum TF-Konto gespeicherte Notizen. **Neu hinzufügen** öffnet Titel (bis 120 Zeichen) und Text (bis 1000 Unicode-Zeichen) mit Restzeichenzähler. Die Liste zeigt Titel und Erstelldatum als **dd.mm.yy HH:MM** (Europe/Berlin), neueste zuerst. Ein Klick öffnet den vollständigen Text; **Bearbeiten** ermöglicht Änderungen. Der Papierkorb pro Zeile löscht nach ausdrücklicher Rückfrage die ganze Notiz. Abbrechen erhält sie. Erstelldaten bleiben bei Bearbeitung unverändert; Revisionsprüfungen schützen vor dem Überschreiben oder Löschen zwischenzeitlich geänderter Notizen. Für Speichern und Laden ist eine Serververbindung nötig; bei Fehlern bleibt die laufende Eingabe erhalten.

Sämtliche zentralen Hilfetexte und die Bedienhinweise im Hilfeleser verwenden die Du-Anrede. Eine eigene gruppierte Notiz-Anleitung sowie eine Prüfung gegen förmliche Anrede sind ergänzt. Android bündelt das Notizmodul zusammen mit dem Portal. Die neue Datenbanktabelle wird durch den bestehenden idempotenten `init_db`-Ablauf angelegt.


### Tagmodus und Nachtmodus

Ein Sonne-/Mond-Symbol im Kopf schaltet die Darstellung für Startseite, TF-Module, gemeinsame Seiten, Verwaltung und Dialoge um. Die Browser-/Geräteauswahl bleibt über Seitenwechsel und Neuladen erhalten; andere Tabs übernehmen Änderungen. Ohne Speicherzugriff funktioniert die aktuelle Seite weiterhin. Der Standard bleibt der Tagmodus. Warnungen, Plan- und Berichtsstatus erhalten eigene dunkle Farben. Originalbilder, Dokumentvorschauen, Unterschriften und Druckausgaben werden nicht invertiert. Die Android-App bündelt dieselben Darstellungsdateien. Die zentrale Du-Hilfe erklärt den Umschalter.

Offline-DS100-Daten werden aus `accounts/stations.json` und `accounts/station_coordinates.json` mit `python tools/build-station-catalog.py` erzeugt; `--check` prüft die Reproduzierbarkeit. Die APK enthält die erzeugte Datei `station-catalog-data.js`.

### TF-Portal-Test und Mitarbeiterpostfächer (0.27.13)

Die Verwaltungskachel **TF-Portal-Aufrufe (Test)** zeigt die letzten 500 erfolgreichen TF-Anmeldungen und Seitenaufrufe mit TF-Nummer, Namen, Datum, Berliner Uhrzeit und Android-Version. Sie ist zunächst nur für Administratoren freigeschaltet; weitere Mitarbeiter benötigen das entsprechende Leserecht. Webaufrufe haben keine Android-Version. Passwörter und Sitzungsschlüssel werden nicht protokolliert. Alte App-Versionen ohne Versionsmeldung können eine leere Versionsspalte haben.

Bei der Neuanlage von TF, Wagenmeistern und Verwaltungsmitarbeitern wird für eine Adresse in einer **verwalteten Maildomain** automatisch ein verschlüsselter Postfachauftrag mit dem Initialpasswort erstellt. Der vorhandene `ctl-mailboxes.timer` verarbeitet ihn auf dem Mailserver. Der Status steht in der Mitarbeiter-E-Mail-Verwaltung. Eine externe Kontaktadresse wird nicht auf diesem Server angelegt. Fehlt die eingerichtete Provisionierung, wird die Neuanlage für verwaltete Adressen mit einer Fehlermeldung abgebrochen. Bestehende Postfächer werden durch normale Stammdatenänderungen nicht zurückgesetzt. App-Passwortänderungen ändern das Mailpasswort nicht automatisch. Keine Neuinstallation und keinen neuen Signierschlüssel erstellen.

GPS-Positionssymbole sind ohne Rahmen und halb so groß. Die Demo zeigt wieder die farbige Geschwindigkeitsspur samt Legende, aber keine Geschwindigkeit am Symbol.

### Manuelle M1-Streckenkenntnis (0.27.14)

Unter **Stecken-, BR- und Ortskenntnisse → Strecken** gibt es **Streckenkenntnis anzeigen** und **Streckenkenntnis anlegen**. Wähle den Startbahnhof oder die Meldestelle per DS100 oder Name. Die Karte zoomt dorthin, sodass Strecke und Betriebsstellen sichtbar sind. Klicke die nächsten Betriebsstellen in der gewünschten Reihenfolge an. Die durchgehende hellgrüne Vorschau folgt der M1-Geometrie. Für mehrere passende VzG-Strecken ist eine ausdrückliche Auswahl erforderlich. Nicht durchgehend oder nicht eindeutig zuordenbare Verbindungen werden nicht gespeichert; ergänze Zwischenpunkte.

Wähle ein Gültigkeitsdatum zwischen heute und höchstens einem Kalenderjahr ab heute und klicke **Speichern**. Erst dann entsteht ein eigener TF-bezogener Kenntnisbestand mit Status **Streckenkundig**. Die Auswahl wird anschließend geleert; die Strecke erscheint in der Anzeige. Es werden keine GPS-Punkte oder fiktiven Erwerbsfahrten erzeugt. Bestehende bestätigte CSV-Kenntnisse werden nicht überschrieben. Zum Speichern ist eine Verbindung erforderlich; bei einem Fehler bleibt die Auswahl erhalten. Die öffentlichen M1-Daten und die Hintergrundkarte sind in der Android-App enthalten.

Die geografische Hintergrundkarte stammt von Natural Earth (1:50m, Public domain): https://www.naturalearthdata.com/about/terms-of-use/ . Quelle und Prüfsummen stehen unter `backend/lokzeitleiste/reference/basemap/`. `python tools/build-m1-basemap.py --check` prüft die erzeugte Browserdatei. Online liegt die OpenStreetMap-Straßenkarte zusätzlich darunter; ohne Internet bleiben Länderumrisse, M1-Netz und Betriebsstellen nutzbar. Der Button **Bahnkarte** behält seinen Namen und schaltet die lokalen M1-Daten statt OpenRailwayMap.
