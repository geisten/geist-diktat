## Nachweis (P2)

`src/diktat.c` versucht ausschließlich `geist_backend_create("cpu_neon", ...)` und anschließend `cpu_scalar`. Der Linux-x64-Build enthält laut GitHub-Buildprotokoll ausdrücklich `cpu_x86` und `cpu_scalar`, aber kein NEON-Backend. Der beschleunigte x86-Pfad wird daher nie ausgewählt.

Der neue Test `Core.test_x86_host_selects_available_accelerated_backend` emuliert eine Backend-Registry mit verfügbarem x86-/Scalar-Backend und fehlendem NEON. Er schlägt auf dem unveränderten Produktquelltext fehl: gewähltes Backend ist nicht x86.

Der echte deutsche WER-Lauf auf dem vorhandenen Linux-x64-Agenten in [Run 33970693518](https://github.com/geisten/geist-diktat/actions/runs/33970693518) wurde deshalb als langsame Scalar-Baseline begrenzt. Der genaue Beschleunigungsfaktor muss mit identischen Dateien separat gemessen werden; aus der Quelltextanalyse allein wird keiner behauptet.

## Lösung und Abnahme

Passendes verfügbares Backend auswählen: x86 auf x86, NEON auf ARM, erst danach dokumentierter Scalar-Fallback. Gewähltes Backend in stderr/Doctor sichtbar machen. Kein unkontrollierter Hardwarezwang: fehlende ISA/Backend-Registrierung sauber behandeln.

Regressionstests für x86-only, NEON-only, Scalar-only und vollständig fehlende Backends. Echte deutsche Audio-Fixtures auf Ubuntu x64 vor/nach Änderung prüfen: WER/S/I/D, RTF, Modellladezeit, Endlatenz und RSS. Numerische Unterschiede müssen sichtbar bleiben; nicht nur die Geschwindigkeit vergleichen. Für den Vergleich eine separate Benchmark-Binary bauen, die aktuelle Produktionsdatei nicht überschreiben.

## Gemessener Vergleich auf dem Ubuntu-Agenten

[Abgeschlossener Vergleichslauf 33971477188](https://github.com/geisten/geist-diktat/actions/runs/33971477188), zwei identische deutsche Clips, 29,1 s Audio / 39 Referenzwörter, gleiche gepinnte Modell-Dateien, je ein frischer Prozess:

| Variante | Gesamtzeit | RTF | WER | max. RSS |
|---|---:|---:|---:|---:|
| Unveränderte Produktion (Scalar) | 115,715 s | 3,976 | 30,8 % | 2.880,3 MiB |
| Temporäre Binary: cpu_x86 statt cpu_neon versuchen | 9,616 s | 0,330 | 17,9 % | 6.210,2 MiB |

Damit ist die Probe hier **12,03× schneller**, benötigt aber deutlich mehr Resident-Speicher. Das ist ein Zwei-Clip-Pilot ohne Wiederholungs-/Signifikanznachweis, keine allgemeine 12×-Garantie. Produktdatei blieb unverändert. Der neue Regressionstest ist im [getesteten Commit](https://github.com/geisten/geist-diktat/blob/44fea7c/tests/test_core.py) veröffentlicht.
