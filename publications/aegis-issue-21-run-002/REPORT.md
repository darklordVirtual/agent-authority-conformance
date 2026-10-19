# AEGIS 3.4.0 — privat reproduksjon, issue #21

**Kjøring 002: fullført med exit 0. Produsentens uendrede fixture rapporterte PASS. Alle fryste forventninger stemte.**

| Måling | Forventet | Målt |
|---|---:|---:|
| Presentasjoner av samme logiske kall | 100 | 100 |
| Fresh execution grants | 1 | 1 |
| Cached replays | 99 | 99 |
| Simulerte downstream-invocations | 1 | 1 |
| Sluttbalanse | 0.000000 | 0.000000 |

Den avgrensede fixture-claimen er ESTABLISHED under denne kjøringen. Sammenligningen mot fryste fixture-forventninger er REPRODUCED. Dette er ikke en utført rerun.py/pakke-rerun og ikke en fullført conformance.lab lifecycle. Klassifikasjon: REPRODUCTION / BCR-1 høyst.

## Bytebinding og miljø

- Produsentcommit: 85e8c96887382cbe77f815a379046329379515f8.
- Fixture SHA-256: 04db8c6b8f655566ae356b03967833ae9fe3fcdb47a237224dabc6295fc2731a.
- AEGIS 3.4.0 wheel SHA-256: 70691ffa689dce033b1488d975aec90b63fc7f2700ad973558cbae46de61921c.
- Plan SHA-256: a2b76a441de2e8f3f43cb781f6ffeb73b6aa7482bd89d7b279ec988697b609eb.
- Forhåndsregistrert før kjøring: https://github.com/darklordVirtual/agent-authority-conformance/commit/00de75cee0141339e631924e2a3ca75d5e71483a.
- Python 3.12.14; cryptography 50.0.2; cffi 2.1.1; pycparser 3.11. Offline wheel-installasjon med hashkrav.
- Import-origin kontrollert fra fresh venv site-packages, uten produsentrepo på import-path.
- Start 2026-10-13T01:27:27.860393Z; slutt 2026-10-13T01:27:30.639758Z.
- Faktisk operatørarbeid for darklordVirtual, AI-assistert av Codex /root i denne sesjonen.

Miljøet har bare én mappet UID/GID, 0; effektive, tillatte og bounding capabilities er null, NoNewPrivs=1 og Seccomp=2. Ingen setuid, privilegieøkning eller ekstra nettverkssandbox ble brukt. Miljøet er ikke en særskilt per-fixture filesystem- eller nettverksgrense. Subprocess fikk kun PATH, HOME, LANG og PYTHONDONTWRITEBYTECODE, ingen arvede credentials. Output/exit ble fanget direkte uten tee-pipeline.

## Første forsøk er bevart

Forsøk 001 stoppet med SETUP_ERROR før AEGIS-import/test fordi UID 65534 ikke finnes i runtime-mappingen. Ingen claim-verdict ble produsert. Forsøk 002 har ny identitet, ny planhash og egen forhåndsregistrering. Ingen historiske records eller produsentbytes er endret.

## Claim-grense

Ett stabilt logisk kall, én prosess, 100 worker threads uten startbarriere. Downstream-effekten er en simulert teller. Ingen garanti om simultaneous start, multi-process drift, eksterne effekter, live settlement, uavhengig implementasjon, sertifisering eller adopsjon. Ingen automatisk oppgradering av A-G eller historisk AEGIS assessment.

## Review og publisering

Status per 2026-10-15: **PRIVATE / FACTUAL_REVIEW_COMPLETED / PUBLICATION_NOT_APPROVED**. Det opprinnelige private e-postarkivet ble sendt LortuArte 2026-10-13 for faktagjennomgang. I svar 2026-10-13 bekreftet LortuArte fakta og aksepterte manuell AACP-operatørfangst og privat levering som tilstrekkelig for den avgrensede BCR-1 / REPRODUCTION-piloten; ingen ekstra conformance.lab-kjøring er etterspurt. LortuArte ba om tre dokumentasjonsrettelser før separat beslutning om publisering. Denne korrigerte kopien er kun til privat oppfølging; **publisering er ikke godkjent**. Ingen offentlige resultatdata skal postes til GitHub; issue #21 forblir åpent.

**Historisk sporbarhet:** `RUN-CAPTURE.json` har `publication_state=PRIVATE_NOT_REVIEWED` fordi dette er status ved innsamling av kjøring 002. Fangstfilen, fryst plan, resultater, fixture, raw logs, leverandørbytes og tidligere forsøk er ikke endret. Denne datert dokumentasjonskorrigeringen er ingen ny kjøring eller endring av testverdict.

Denne **private e-post-/review-kopien** inneholder rå stdout/stderr, pip freeze, import-origin, capture-record, fryst plan, fixture, lockfile, lisens og SHA-256-manifest, men **ikke binære wheel-filer**. Wheel-filene med eksakte SHA-256-hasher er beholdt i den separate komplette private evidenspakken. Hashene/pins for distribusjon og avhengigheter er dokumentert i `requirements.lock` og `RUN-PLAN-FROZEN.json`. `SHA256SUMS` gjelder de faktiske filene i denne review-kopien.
