## Reproduzierbarer Befund (P2)

Die neue reale Modellmessung unter macOS produziert bei kontrolliertem Zusatzrauschen ungesprochenen Erklärungstext bzw. englischen Text, obwohl die Referenz deutsches Diktat ist. Alle Prozesse enden mit Exit 0. Dies ist ein beobachteter Qualitätsfehler; die Ursache ist noch nicht auf VAD, Encoder, Prompt oder Decoder eingegrenzt.

Gepinnt: Produktquelltext wie `607d194`, Engine `bb751c596f7d6ed3f73fa2d4c4e29e617cada57f`, Q4_K_M SHA `740185b21d22ceb83a11c3aa62ad5842ef32c70f6096d756bbee85a1e4ec34b8`, Tower SHA `d6c45a6c276212dc3a793e66dfc588d89c12d1ac92c0e4b85494390ca848cd77`.

Fixtures aus [FLEURS](https://huggingface.co/datasets/google/fleurs), Revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`, menschliche Stimme plus deterministisches simuliertes Mikrofon-Eigenrauschen/50-Hz-Brummen:

- `fleurs-10058186628567796965-snr5`: 21 Referenzwörter, 17 Substitutionen und 26 Einfügungen, WER 204,8 %. Der Output wird zu einer erklärenden Antwort.
- `fleurs-10058299886985225661-snr10`: 16 Referenzwörter, 15 Substitutionen und 15 Einfügungen, WER 187,5 %.
- Sechs identische Sätze: sauber 9/130 Fehler (6,9 %), bei 20/10/5 dB Zusatzrauschen 20/71/132 Fehler (15,4/54,6/101,5 %).

## Reproduktion

[Fixture-Aufbereitung](https://github.com/geisten/geist-diktat/blob/cb443da/benchmarks/prepare_quality.py) und [Evaluator](https://github.com/geisten/geist-diktat/blob/cb443da/benchmarks/quality.py): `python3 benchmarks/prepare_quality.py`, anschließend `quality.py --groups de-noise-10db,de-noise-5db` mit den gepinnten Modellpfaden. Seed 20260905; SNR relativ zur RMS aktiver 20-ms-Sprachframes. Ausgabe bleibt auswertbar, auch wenn WER über 100 % liegt.

## Abnahme

Ursachen durch A/B von VAD, Sprachrauschen, Streaming und Transkriptionsprompt eingrenzen. Rauschen ohne Sprache als negative Kontrolle ergänzen. Halluzinations-/Sprachwechselrate und S/I/D getrennt messen. Keine unbekannte Sicherheit aus einem Konfidenzwert ableiten; bei schlechter Aufnahme sichtbare Qualitätswarnung bzw. bestätigungsfähigen Text anbieten. Keine pauschale Filterung, die echte Diktate stillschweigend löscht. Fix auf sauberen und verrauschten deutschen, Dialekt- und Langzeitdaten auf Mac/Pi/Ubuntu regressionsprüfen.
