# Externer Pilot vor der öffentlichen Ubuntu-Beta

Status: **Vorgehen beschlossen, Durchführung und Nutzennachweis offen.** Grundlage
sind die bestätigten Antworten Q8, Q9, Q12, Q15–17 des Grilling-Interviews und der
[Produktplan](PRODUCT-PLAN.md). Dieses Dokument definiert den Test; es berichtet
keine bereits gewonnenen Teilnehmer oder erzielten Zeitgewinne.

## Zweck und Freigaberegel

Direktes Diktieren einschließlich Korrektur muss schneller zum brauchbaren Text
führen als Tippen. Beide Pflichtkategorien werden separat ausgewertet:

- **Alltagstexte:** beispielsweise E-Mails, Notizen und kurze Dokumentabsätze.
- **Technische Texte:** beispielsweise Problembeschreibungen und KI-Prompts mit
  deutschen und englischen Fachbegriffen, Zahlen, Dateinamen oder Bezeichnern.

Für jede Kategorie gilt unabhängig:

1. Median der personenbezogenen Zeitgewinne **mindestens 25 %**.
2. **Mindestens vier von fünf Personen** sind schneller als beim Tippen.
3. Die verglichenen Endtexte erfüllen die vorab definierten Inhaltsanforderungen.
   Unkorrigierte Fehler dürfen keinen scheinbaren Zeitgewinn erzeugen.

Ein gutes Ergebnis einer Kategorie kann ein schlechtes der anderen nicht ausgleichen.
Die Regeln sind verbindlich; WER-, Live-, Installations- und Einbettungsgates bleiben
zusätzliche Voraussetzungen. Der Pilot ist klein und liefert keine repräsentative
Aussage über alle Nutzer oder Überlegenheit gegenüber anderen Diktatprodukten.

## Teilnehmer und Verantwortung

Germar gewinnt mindestens fünf externe Teilnehmer aus seinem Umfeld. Das Projekt
bereitet Aufgaben, Messvorlage und Auswertung vor. Eine Kontaktaufnahme oder
Nachricht an Teilnehmer ist damit noch nicht erfolgt.

Die erste auswertbare Kohorte umfasst fünf vorab benannte Personen. Erfahrung mit
Linux, Tippen und Diktat sowie Mikrofon und Hardware werden dokumentiert; keine
Kenntnis der Projektinterna voraussetzen. Beide Textkategorien von allen Personen
bearbeiten lassen. Keine nachträgliche Auswahl der fünf besten Ergebnisse. Größere
Folgekohorten bekommen vorab dieselbe prozentuale Regel: mindestens 80 % der
Teilnehmer schneller, auf ganze Personen aufgerundet.

## Vor dem ersten gewerteten Durchgang einfrieren

- Ubuntu-/GNOME-Version und Sitzungstyp; konkrete App-Versionen und Paketformate.
- Freigabekandidat mit Commit, Binary-/Modellhash, Backend und Parametern.
- Fünf verbindliche Anwendungen: Vim, Neovim, festgelegter GNOME-Texteditor,
  Firefox und LibreOffice Writer. Die technische App-Abnahme bleibt vollständig;
  nicht jede Person muss jede Anwendung als Zeitvergleich bedienen.
- Pro Kategorie mehrere vergleichbare Aufgabenpaare, deren Reihenfolge und
  Zuordnung zu Tippen/Diktieren vorab festgelegt werden. Anwendung je Paar gleich.
- Gleicher erwarteter Inhalt und ähnliche Länge/Schwierigkeit beider Varianten;
  keine rein mechanische Wiederholung desselben Textes als zweite Messung.
- Regeln für korrekte Endtexte, darunter Zahlen, Negationen, Fachbegriffe und
  Bezeichner. Bei freien Formulierungen zulässige Varianten vorab festlegen.
- Identische kurze Eingewöhnung für beide Verfahren; Übungsaufgaben nicht werten.
- Keine generative Textumschreibung als unbeobachtete zusätzliche Schreibhilfe.
  Sonstige Schreibhilfen und Korrekturoptionen dokumentieren und konstant halten.

Tippen und Diktieren in wechselnder Reihenfolge durchführen. Aufgaben und Geräte
nicht nach Einsicht in Ergebnisse austauschen. Das Pilotmaterial wird nicht zur
Anpassung des Kandidaten vor genau dieser Abnahme verwendet.

## Messung und Berechnung

**Einrichtung separat:** Alle fünf müssen den Erststart ohne Terminal-Diagnose
oder Projekt-/Entwicklerhilfe bewältigen. Klicks, Berechtigungsdialoge, Downloads,
Einrichtungszeit und Hilfebedarf dokumentieren. Entwicklerabhängigkeiten dürfen auf
den Prüfsystemen nicht versehentlich die Paketprüfung ersetzen.

**Nutzung:** Nach Einrichtung beginnt die Zeit mit dem Start der Aufgabe im
festgelegten Zielfeld. Beim Diktieren gehören Shortcut, Startbereitschaft,
Erkennung, Pausen, Einfügung, Stop und sämtliche Nachkorrekturen zur Messung.
Beim Tippen gehören Eingabe und sämtliche Nachkorrekturen dazu. Ende ist die
Fertigmeldung des korrigierten Textes. Kalt-/Warmzustand des Dienstes dokumentieren;
kein unbeobachtetes Vorwärmen außerhalb der vereinbarten Startbedingung.

Endtexte werden anschließend unabhängig gegen die Aufgabenanforderungen geprüft.
Bei einem ungültigen Endtext gilt die Aufgabe als nicht bestanden, nicht als
schneller Erfolg. Abbrüche, falsche Einfügeziele und fehlende Messungen bleiben im
Bericht und verhindern eine vollständige Abnahme; sie werden nicht aus dem Median
herausgefiltert. Neue gültige Durchgänge brauchen nachvollziehbare Wiederholungs-
regeln und vergleichbare neue Aufgaben, statt schlechte Einzelwerte zu ersetzen.

Für Person p und Kategorie k werden die vorab zugeordneten gültigen Aufgabenzeiten
je Verfahren summiert:

```
T_tip(p,k)  = Summe der Zeiten bis zum korrigierten Text beim Tippen
T_dict(p,k) = Summe der Zeiten bis zum korrigierten Text beim Diktieren
G(p,k)     = 1 - T_dict(p,k) / T_tip(p,k)
```

Beide Summen müssen vollständig und positiv sein. Für jede Kategorie separat den
Median über die fünf Werte G(p,k) berechnen und die Anzahl G(p,k) > 0 zählen.
**Bestanden: Median ≥ 0,25 und Anzahl ≥ 4**, mit vollständigen gültigen Pflichtaufgaben.
Keinen Quotienten der gruppenweit summierten Zeiten als Ersatz verwenden: Sonst
würden einzelne langsame Teilnehmer das Ergebnis überproportional bestimmen.

Rechenbeispiel, **keine Messung**: personenbezogene Gewinne 10 %, 20 %, 25 %, 30 %,
40 % bestehen eine Kategorie. Gewinne −5 %, 5 %, 10 %, 15 %, 90 % bestehen sie
nicht, obwohl ein einzelner Teilnehmer stark profitiert.

## Auswertungsartefakte und Veröffentlichung

Die noch zu erstellende Messvorlage enthält je Aufgabe mindestens:
`participant_id`, Kategorie, Aufgabenpaar, Variante, Methode, Reihenfolge,
App-/Paketversion, Kandidat, Hardware/Mikrofon, Startzustand, Dauer,
Endtextprüfung, Fehler/Abbruch und Hilfeleistung.

Der Bericht enthält:

- Erststart-Ergebnis je Person sowie App-/Geräte-/Versionsprofil.
- Beide Zeitsummen und Zeitgewinn je Person und Kategorie; Median und Anzahl
  schnellerer Teilnehmer je Kategorie, vollständige Fehler-/Abbruchübersicht.
- Zugehörige unabhängige WER-/Live-/Installations- und App-Abnahmen.
- Grenzen der kleinen Stichprobe und Änderungen gegenüber früheren Kandidaten.

Personen pseudonymisieren. Audio und Texte nur mit ausdrücklicher Zustimmung
speichern oder veröffentlichen; ansonsten numerische Evidenz und Aufgabenmethodik
bereitstellen. Der Test darf keine privaten Arbeitsinhalte als notwendige Eingabe
voraussetzen.

Bei Nichtbestehen wird der Kandidat überarbeitet und erneut abgenommen. Die
Veröffentlichung wartet; die vereinbarten Grenzen werden nicht nachträglich
zugunsten eines Termins gelockert. Nach Bestehen werden öffentliche Vorstellung,
Demo, nachvollziehbare Ergebnisse und installierbarer Beta-Download gemeinsam
vorbereitet. Der tatsächliche Release ist durch dieses Protokoll nicht erfolgt.
