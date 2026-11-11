# Mitarbeiterpostfächer, Anmeldung und Oberfläche

Die vollständige Neuinstallation für Ubuntu 26.04 bleibt `install-ctlsoftware-test.sh`. Für den bereits eingerichteten eigenständigen CTL-Testserver unterstützt die Datei jetzt zusätzlich `--update`.

## Bestehenden Server aktualisieren

Der bestehende Server unter https://ctl-software.io-goerlitz.eu verwendet Apache und MariaDB ohne Docker. Quellcode: `/opt/ctlsoftware-test-source`; laufendes Backend: `/opt/ctlsoftware-test/backend`; Konfiguration: `/etc/ctlsoftware-test/app.env`. Lokale Änderungen vor dem Update mit `git status --short` prüfen und erhalten. Bei einem Fast-Forward-Konflikt anhalten und die Änderungen klären; keinen erzwungenen Reset verwenden.

```bash
cd /opt/ctlsoftware-test-source &&
git pull --ff-only origin setup/debian-testumgebung &&
sudo bash install-ctlsoftware-test.sh --update --source /opt/ctlsoftware-test-source
```

`--update --source` aktualisiert die vorhandene Anwendung aus diesem Checkout. Keine Neuinstallation, kein `--resume` und kein `setup-update.sh` für diese Installation ausführen. Die vorhandene Konfiguration weiterverwenden; keine neue Datenbank oder Docker-Umgebung einrichten. Das Update sichert Datenbank, Konfiguration und Backend unter `/etc/ctlsoftware-test-setup/backups/`. Bei einem Fehler die Sicherung aufbewahren und die Meldung prüfen; es erfolgt kein automatisches Restore.

Danach prüfen:

```bash
sudo systemctl status ctlsoftware-test.service ctlsoftware-test-worker.service --no-pager
sudo journalctl -u ctlsoftware-test.service -u ctlsoftware-test-worker.service -n 80 --no-pager
curl --fail --show-error https://ctl-software.io-goerlitz.eu/health
```

Portal neu laden und die Softwareinformation auf **0.26.39** prüfen. Anmeldung, Arbeitsbericht und einen PDF-Download testen. Eine neue gebündelte Android-Hilfe erfordert zusätzlich die aktuelle signierte APK über der bestehenden App.



## Persönliche E-Mail-Adressen

Die 20 importierten Demo-TF erhalten einmalig persönliche Adressen unter `ctl-software.io-goerlitz.eu`. Ihre bisherige gemeinsame Profiladresse wird ersetzt; Portalpasswörter werden nicht zurückgesetzt. Das anfängliche Postfachpasswort ist `tomcom123456`. Die Demo-Postfächer werden bei späteren Updates nicht erneut zurückgesetzt.

Neue TF und Verwaltungsmitarbeiter erhalten bei Auswahl einer verwalteten Domain ein Postfach mit demselben Initialpasswort wie im Portal. Das Postfachpasswort und das Portalpasswort sind anschließend eigenständige Zugangsdaten; eine spätere Portalpasswortänderung ändert das Mailpasswort nicht.

In App Grundwerte werden die Maildomains gepflegt. Die Vorschläge haben das Muster `vorname.nachname`; Umlaute werden als ae/oe/ue und ß als ss geschrieben. Bei Kollision folgt das zweistellige Geburtsjahr, bei weiteren Kollisionen eine laufende Zahl. Der Server prüft die Eindeutigkeit erneut. Bereits angelegte lokale Postfächer können durch eine reine Profiländerung nicht umbenannt werden, damit Nachrichten und Zugangsdaten nicht verloren gehen.

„Eigene Domain“ erlaubt eine vollständige externe Adresse mit Formatprüfung. Ein externes Postfach wird dadurch nicht bei STRATO, Gmail oder einem anderen Anbieter angelegt und erhält keine lokalen Zugangsdaten. Versand aus dieser Adresse benötigt eine separat eingerichtete Mailverbindung.

Zusätzliche verwaltete Domains müssen dem Betreiber gehören und beim Provider passend eingerichtet werden: A/MX auf diesen Server, SPF, DKIM mit dem bestehenden ctl-Schlüssel für die zusätzliche Domain und DMARC. Der Mailclient verwendet weiterhin den zertifizierten Servernamen `ctl-software.io-goerlitz.eu`. Domainauswahl allein ändert keine Provider-DNS-Einträge.

Die vier bisherigen Funktionspostfächer info/diso/vkplanung/railpool bleiben erhalten und leiten weiterhin zusätzlich an Gmail weiter. Persönliche Mitarbeiterpostfächer werden nicht an die frühere Gmail-Defaultadresse weitergeleitet.

## Technische Postfachanlage

Die Webanwendung schreibt verschlüsselte Aufträge in `mailbox_provisions`. Der root-eigene, nicht durch die Anwendung veränderbare Dienst `ctl-mailboxes.service` verarbeitet sie ungefähr alle 15 Sekunden über `ctl-mailboxes.timer`. Er validiert Domain und Adresse, erstellt Maildir und Dovecot-Passworthash und aktualisiert die Postfix-Maps. Die Webanwendung erhält weder sudo noch Root-Rechte. Der Status „Wird angelegt“ bleibt bis zum erfolgreichen Abschluss sichtbar.

```bash
sudo systemctl status ctl-mailboxes.timer
sudo journalctl -u ctl-mailboxes.service -n 60 --no-pager
```

Der Backend-E-Mail-Bereich listet alle TF und Verwaltungsmitarbeiter. Auswahl öffnet den Versand mit der jeweiligen Mitarbeiteradresse als Absender, An, CC, BCC und maximal fünf Anhängen (zusammen 7 MiB, kodierte Gesamtnachricht maximal 10 MiB). BCC-Adressen werden als SMTP-Empfänger übermittelt und nicht im gespeicherten Nachrichtenkopf abgelegt. Lesen/Schreiben im E-Mail-Modul erlaubt den Versand mit den dort verwalteten Mitarbeiterkonten.

## Oberflächen und Anmeldung

- `/`: zwei Kacheln für TF-Portal und Verwaltung.
- Administratoren sehen auf `/admin/start` außerdem phpMyAdmin und Webmailer.
- Nach Login erfolgt die Weiterleitung auf das Dashboard des jeweiligen Bereichs; ein erforderlicher Initialpasswortwechsel hat Vorrang.
- Portal und Verwaltung verwenden getrennte Cookie-Namen und pro Browser-Tab gespeicherte Tokens. Ein TF-Tab und ein Verwaltungs-/Administrator-Tab können gleichzeitig angemeldet bleiben. Neue Tabs mit `/tf` beziehungsweise `/admin` öffnen.
- Fahrzeugnummern beginnen bei neuen Fahrzeugen mit 91 und 80, beide Werte sind änderbar. Nach vollständiger Eingabe eines Nummernblocks springt der Fokus zum nächsten Feld.
- App-Grundwerte für Grund/Art zeigen kompakte Auswahllisten. Bearbeitungsaktionen erscheinen erst nach Auswahl.

## Prüfung

Automatisierte API-Tests prüfen Adressbildung, Kollisionen, verschlüsselte Anlageaufträge, Domainvalidierung und gleichzeitige TF-/Admin-Identitäten. SMTP-/IMAP-Komponenten werden in den Tests simuliert. Die zusätzliche echte Postfachanlage und der Versand aus neuen TF-Adressen müssen auf dem Server abschließend geprüft werden; eine bestätigte frühere Zustellung belegt nicht die neuen Funktionen.
