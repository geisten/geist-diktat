## Problem und Nachweis

Asynchrone Capture-/Enginefehler und Job-Rennen machen den sichtbaren Aktivstatus aktuell unzuverlässig. Alltagstaugliche globale Integration braucht eine überprüfbare Mikrofon- und Zielanwendungsanzeige.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

## Abnahmekriterien

Status idle/loading/listening/decoding/error mit sichtbarem Mic-Indikator, globalem Stop und Wiederaufnahme. Fokuswechsel und geschützte Felder haben explizite Regeln. Standardmäßig keine Audio-/Transkriptpersistenz; Diagnoseexport redigierbar.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
