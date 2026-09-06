## Problem und Nachweis

Die CLI transkribiert auf macOS; eine systemweite Einfügung mit globalem Hotkey und geführter Mikrofon-/Bedienungshilfen-Freigabe ist nicht vorhanden.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

## Abnahmekriterien

Signierte/notarisierte installierbare App oder dokumentierter Eingabedienst mit globalem Shortcut, Mic-Status, Stop, Gerätewechsel und Onboarding. TextEdit, Browser, Terminal sowie Vim/Neovim getrennt testen; Secure-Input/Passwortfelder nicht beschreiben, Clipboard erhalten.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
