# Android 0.26.49 – aktuelles TF-Portal

Die App öffnet nach der nativen Anmeldung das vollständige TF-Portal. Die gemeinsamen HTML-/CSS-/JavaScript-Dateien werden beim Android-Build aus `backend/lokzeitleiste/static` in die APK übernommen. Geschäftsregeln, Tabellen, Eingaben und Berechtigungen entsprechen damit dem Portalstand dieses Builds. Neue Portalversionen erfordern einen neuen APK-Build. Der Server muss mindestens zum selben Projektstand aktualisiert sein.

Enthalten sind Arbeitsberichte mit Dienstarten, Pausen, Ausbleibe, Gastfahrten und optionalen Selbstzahlerbelegen; Zugfahrten und Ereignisse mit dynamischen Grundwerten; Monatslisten und Synchronisation; GPS mit Standzeiten, ZMS-Vorschlägen und Gründen; Arbeitsplan; Dokumentenverwaltung mit Upload/Download; Bahnhofsverzeichnis einschließlich Kontaktdaten, Plänen, Teilen und Zwischenablage; Konto, Passwortwechsel und Deutsch, Polnisch und Englisch. Das Lokübergabebuch zeigt die gemeinsame Fahrzeugliste und Fahrzeugdetails mit Status und Einschränkungen an. Übergabeprotokolle können fahrzeugbezogen mit Anhängen erfasst und von allen TF gelesen werden. PZB und Störungen sind noch Platzhalter; ebenso das Leuna-Übergabeprotokoll.

## Vorhandene Daten

**Bisherige Erfassungen** öffnet die vorherige native Monats-/LokZeit-Erfassung. Ihre Daten werden nicht gelöscht oder automatisch als neue Arbeitsberichte doppelt übertragen. **zurück TF-Portal** führt zurück. Browserentwürfe auf einem anderen Gerät werden nicht automatisch übernommen; synchronisierte Berichte erscheinen über den Server.

## Offline und Synchronisation

Nach einer erfolgreichen Online-Anmeldung kann das gebündelte Portal ohne Netz erneut geöffnet werden. Arbeitsberichte und Quittungen verwenden wie im Browser LocalStorage bzw. IndexedDB. Zuletzt abgerufene Pläne und Suchergebnisse sind in einem begrenzten, kontogetrennten Zwischenspeicher verfügbar; Berichtslisten nutzen zusätzlich den vorhandenen Monatscache. Nicht die gesamte Serverhistorie ist offline verfügbar. Neue Bahnhofssuchen und serverseitige Änderungen benötigen eine Verbindung. Lokale Arbeitsberichte über **Synchronisieren** übertragen; es gibt keinen unbeaufsichtigten automatischen Versand aller Dokumente. Uploadfehler löschen keine lokalen Belege. HTTP 401/403 wird nicht durch einen Offline-Cache übergangen. Eine Offline-Abmeldung entfernt die Sitzung auf dem Gerät; eine serverseitige Sperrung kann offline erst beim nächsten Kontakt erkannt werden.

## GPS unter Android

1. Arbeitsbericht öffnen, Zugfahrt hinzufügen und Zugnummer eintragen.
2. **Zugfahrt per GPS aufzeichnen** antippen, präzisen Standort erlauben und Android-GPS einschalten.
3. Die dauerhafte Systembenachrichtigung zeigt die laufende Aufzeichnung. Der Standortdienst läuft unabhängig vom WebView, auch bei Bildschirmsperre.
4. In derselben Zugfahrt **GPS-Aufzeichnung beenden** wählen und bei Netzverbindung synchronisieren. Standzeiten/ZMS/Gründe werden mit der vorhandenen Serverauswertung bearbeitet.
5. **GPX herunterladen** öffnet die Android-Dateiauswahl.

Standortpunkte werden zusätzlich im privaten App-Verzeichnis protokolliert und beim Wiederöffnen der Zugfahrt übernommen. Prozessabbruch, „Stopp erzwingen“, entzogene Berechtigungen, Stromsparregeln oder fehlender Satellitenempfang können die Aufzeichnung unterbrechen. Nach einem solchen Abbruch die betroffene Zugfahrt öffnen und ausdrücklich fortsetzen oder beenden. Es wird kein lückenloser Verlauf erfunden. Kein automatischer Start bei Geräte-Neustart. Keine Hintergrundstandortberechtigung und kein kostenpflichtiger Kartenanbieter erforderlich; die bestehende kostenlose OSM/ZMS-Abfrage läuft über den Server.

## Dateien und Anmeldung

Uploads verwenden die Android-Dokumentenauswahl; die vorhandenen 10-MB-Grenzen werden weiter geprüft. Downloads werden nur vom konfigurierten Server mit der eigenen Sitzung abgerufen und am gewählten Ort gespeichert. PDFs behalten Dateiname, UTF-8-Zeichen, `.pdf` und `application/pdf`. Im System-Speicherdialog Zielordner wählen und Speichern bestätigen; Abbrechen beendet den Vorgang ohne Download. Nach dem Speichern öffnet Ansehen eine passende Dokumenten-App. GPX-Dateien werden in kleinen Blöcken an die native Dateiauswahl übergeben. Fremde Webseiten öffnen außerhalb der Portal-WebView. TLS-Fehler werden nicht übergangen. Die native Bridge ist auf den exakten Serverursprung und das Hauptfenster beschränkt.

## APK bauen und installieren

Voraussetzungen: JDK 17, Android SDK Plattform 35/Build Tools 35.0.0 und Gradle 8.9 (oder Android Studio mit passender Gradle-Konfiguration). Im Projektverzeichnis:

```bash
gradle :app:testDebugUnitTest :app:assembleDebug :app:lintDebug \
  -PlokzeitleisteApiBaseUrl=https://ctl-software.io-goerlitz.eu
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Bei einer APK mit anderer bisheriger Signatur kann Android kein direktes Update installieren. Vor einer Deinstallation unübertragene lokale Daten sichern/synchronisieren. Keine Deinstallation ohne Datensicherung empfehlen.

Die GitHub Action **Android TF Portal APK** prüft Unit-Tests, Build, Lint und APK-Übersetzungen. Mit den bereits eingerichteten Signierungs-Secrets veröffentlicht sie die signierte APK und `update.json` als öffentliches `android-test-…`-Release in RailSoftware. [Erstinstallation, vorhandener Mac-Schlüssel und Updates](ANDROID-STUDIO-TABLET.md). Für normale Tablet-Updates die Release-APK statt eines lokalen Builds verwenden; der lokale Standard-versionCode 75 liegt unter dem bestätigten Tabletstand 100004.

Die App prüft beim Öffnen/Fortsetzen höchstens alle sechs Stunden; **Updates → Auf Updates prüfen** prüft sofort. Sie lädt die APK automatisch, prüft Prüfsumme, Paket, höhere Version und Signatur. Offene Eingaben speichern, GPS beenden, **Update installieren** wählen und Android bestätigen. Bei Bedarf für die App **Aus dieser Quelle zulassen** aktivieren. Über die bestehende App installieren; nicht deinstallieren.

Der bestehende HTTPS-Server wird gemäß [Standalone-Anleitung](../../docs/INSTALL-CTLSOFTWARE-TEST.md#bestehenden-server-aktualisieren) aktualisiert.

Zum lokalen Emulator-Test:

```bash
gradle :app:assembleDebug -PlokzeitleisteApiBaseUrl=http://10.0.2.2:8080
```

Das HTTP-Ausnahmeziel gilt nur für den Debug-Emulator. Release-Builds benötigen HTTPS.

## Prüfstatus

Die gemeinsame Portal-/GPS-Logik und Android-Adapter sind durch automatisierte Simulationen und Backendtests abgesichert. Die GitHub Action ergänzt Android-Kompilierung, Unit-Tests und Lint. Reale GPS-Qualität, Bildschirmsperre, Dateiauswahl und Verhalten bei Energiesparregeln müssen auf einem echten Android-Gerät geprüft werden.

## Karten, Nachtdienst und GPS-Zeit ab 0.26.39

Android erlaubt gezielt öffentliche PNG-Kartenkacheln von OpenStreetMap und OpenRailwayMap über HTTPS. Anmeldung, API und Dateien bleiben auf den konfigurierten Server beschränkt. Kartenbilder benötigen Internet. Der GPS-Start berücksichtigt das eingetragene Enddatum eines Nachtdienstes. Die grüne Zeitanzeige enthält die gesamte Zeit seit der erkannten Abfahrt einschließlich Zwischenhalten und Zeitlücken; die rote Anzeige addiert weiterhin GPS-Standzeiten. Signalverlust erzeugt keine Standzeit.

## GPS-Lücken und manuelle Halte ab 0.26.41

Die Karte schließt Signalunterbrechungen mit einer hellrosa Geraden. Diese geschätzte Verbindung ändert keine GPS-Rohpunkte und zählt nicht automatisch als Standzeit. Start Stand wird während einer laufenden GPS-Aufzeichnung bei einer Lücke freigegeben (mehr als 30 Sekunden ohne genauen neuen Punkt oder ein ungenauer Punkt). Ende Stand bleibt auch nach Signalrückkehr bedienbar. Manuelle Halte in einer Lücke erscheinen gelb-rot. Ihre Position auf der Verbindung ist aus der Startzeit geschätzt; bis zur Signalrückkehr wird die letzte bekannte Position verwendet. Zeiten und Gründe bleiben manuelle Angaben. Die rote Zeitsumme zählt Überschneidungen mit gemessenen Halten nur einmal. GPS-Start/-Stopp und manueller Halt bleiben getrennte Vorgänge.

## GPS-DEMO ab 0.26.43

Die eigene Kachel GPS-DEMO öffnet `/tf/gps-demo`. Synchronisiere vorher eine beendete GPS-Aufzeichnung. Wähle sie nach Zugnummer und Datum aus und lade sie. Abspielen/Pause, Zum Anfang, ein Zeitregler und 1× bis 300× steuern die Wiedergabe. Fünf Stunden dauern bei 300× eine Minute. Die Demo verwendet die vorhandene Karte mit Zugposition, Spur, Standzeiten und markierten GPS-Lücken. Sie startet weder Android-GPS noch Hintergrundaufzeichnung und schreibt keine Arbeitsberichte oder GPS-Aufzeichnungen. Beim Ausblenden oder Verlassen pausiert sie. Laden und Kartenbilder benötigen Internet.

## Android-Anmeldung ab 0.26.45

Der Login zeigt das Rail-Software-Logo und einen abgerundeten Rahmen aus Schienen und Schwellen in den Logofarben Weinrot/Dunkelblau. Die Karte ist horizontal und vertikal zentriert. Bei wenig Höhe oder geöffneter Tastatur lässt sie sich scrollen. TF-Nummer und Passwort stehen untereinander, gefolgt von Anmelden und dem Hinweis zur gespeicherten Anmeldung. Zur Erstanmeldung nutzt Du das Admin-Passwort und änderst es anschließend wie bisher. Nach drei abgewiesenen Anmeldungen derselben TF-Nummer erscheint Passwort vergessen. Der Dialog verweist an Deinen Administrator; ein automatischer Selbstbedienungs-Reset ist nicht eingerichtet. Netzwerkfehler zählen nicht als Passwort-Fehlversuche. Eine bestehende Anmeldung bleibt nach dem App-Update erhalten; der neue Bildschirm erscheint bei der nächsten Anmeldung.

## Updates und DB Digi-Bef. ab 0.26.46

Die native obere Leiste mit TF Portal, Bisherige Erfassungen, Abmelden und Update entfällt. Abmelden verwendest Du im Portal-Header. Die eigene Kachel Updates enthält installierte Android-Version, Web-Version, sofortige Prüfung, Installation und die letzten Versionsänderungen. Die automatische Sechs-Stunden-Prüfung samt Download bleibt bestehen; eine Installation öffnest Du ausdrücklich. Im Login erscheint zusätzlich Update, sobald eine neuere passende APK heruntergeladen und geprüft ist. Beim Öffnen des Logins wird einmal sofort geprüft. Android bestätigt weiterhin die Installation. Vorher offene Eingaben speichern und GPS beenden.

DB Digi-Bef. im GPS-Bereich öffnet dieselbe externe DB-Seite wie die Kachel Digi-Befehle. Die bereits gestartete native GPS-Aufzeichnung bleibt im Hintergrund aktiv; zurück in der App werden die protokollierten Punkte übernommen. Optional kannst Du Art DB InfraGo und Grund DB-Digi-Befehl für den aktuellen Halt bestätigen. Gibt es keinen aktuellen Halt, beginnt eine manuelle Standzeit. Beende sie nachher mit Ende Stand und ergänze Ort und Grund vor dem Übernehmen. Beim Abbrechen der Nachfrage wird nur die DB-Seite geöffnet. Eine Bestätigung darf nur bei tatsächlichem Halt erfolgen.

## Arbeitsbericht ab 0.26.47

Die drei Reiter verwenden das Design der Zugfahrten: **Dienstzeit und Gastfahrt**, **Zugfahrt und Details (GPS)** und **Arbeitsberichte des Monats**. Du wechselst ohne Verlust Deiner Eingaben; eine laufende GPS-Aufzeichnung läuft weiter. Ein neuer oder geöffneter Bericht zeigt Dienstzeit, eine wiederhergestellte GPS-Aufzeichnung den GPS-Reiter. Pflichtfeldfehler öffnen den passenden Reiter. Ein anderer Bericht kann während einer laufenden GPS-Aufzeichnung weiterhin nicht geladen werden.
