## Problem und Nachweis

Neovim-Plugin liegt im Repository, ist aber nicht automatisch über die geprüften .deb-/Tarball-Installationswege einsatzbereit. Geschlossene Vorgänger #4/#6 decken diesen Erststart nicht ab.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

## Abnahmekriterien

Neovim-Paketpfad/lazy.nvim-Beispiel und Vim-Paket anbieten; ein Setup-Schritt setzt Runtimepfad und dokumentierte Taste. Installieren, Update, Deinstallation und frisches HOME automatisiert testen; vorhandene Nutzerkonfiguration erhalten.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
