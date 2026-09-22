# Operazioni sul server

Tutti i comandi vanno eseguiti sul server 192.168.11.10.
Il computer locale è soltanto client SSH/browser. Se il server non risponde,
fermarsi senza creare ambienti sostitutivi.

    ssh -o HostName=192.168.11.10 ASC-OLB-WFO-01
    cd /opt/asc/wms/WMS-per-studi

L'alias SSH può contenere un IP superato: usare l'override esplicito.

## Inventario e segreti

Container: asc-wms-dev, asc-wms-test, asc-wms-prod.
Dati: /opt/asc/wms/data, directory separate per ambiente.
TEST SQL: asc-wms-test-postgres, rete asc-wms-test-db e volume
asc-wms-test-postgres-data, senza porta database pubblicata sull'host.

I file /opt/asc/wms/secrets/test-postgres.env e test-database.env restano
esterni al repository, permessi 600. Il primo contiene POSTGRES_USER,
POSTGRES_DB e POSTGRES_PASSWORD; il secondo WMS_DATABASE_URL.
Non stampare o copiare i valori nei log o in GitHub.

## Build e aggiornamento TEST

    docker build --build-arg WMS_REVISION="$(git rev-parse --short HEAD)" -t asc-wms:test-NOME-RILASCIO .

Usare un tag nuovo e aggiornare l'immagine in compose.database-test.yaml.
Conservare tag precedente e backup. Il rilascio del 22 settembre usa
asc-wms:test-validation-20260922. Aggiornare solo il servizio richiesto:

    docker compose -f compose.yaml -f compose.database-test.yaml up -d --no-build --no-deps wms-test
    curl -fsS http://127.0.0.1:8001/api/health
    curl -fsS http://127.0.0.1:8001/api/runtime

--no-deps presuppone il database attivo. Per il primo avvio vedere
[database-repertorio.md](database-repertorio.md).
Il runtime deve dichiarare TEST, angular, postgresql.
Verificare accesso, ruoli, Clienti → Modifica → REPERTORIO e pratiche storiche.
La build non trasferisce modifiche negli altri ambienti.

## Backup e ripristino

Per un punto coerente, fermare il backend durante la copia di SQL e file.
Usare una directory datata sotto /opt/asc/wms/backups, con accesso ristretto.
Conservare SQL, intera directory dati TEST, configurazione e tag immagine.
Docker inspect può contenere segreti: resta nel backup.

    docker stop asc-wms-test
    docker exec asc-wms-test-postgres pg_dump -U wms_test -d wms_test -Fc > /PERCORSO-BACKUP/test.dump
    tar -czf /PERCORSO-BACKUP/test-files.tgz -C /opt/asc/wms/data test
    docker start asc-wms-test

Sostituire /PERCORSO-BACKUP con una directory reale sul server. Gestire il
riavvio anche in caso di errore; un backup fallito non è un punto di ripristino.

Per un ripristino deliberato: fermare TEST, salvare il suo stato corrente come
punto di ritorno, verificare origine e integrità del dump e ripristinare:

    docker exec -i asc-wms-test-postgres pg_restore -U wms_test -d wms_test --clean --if-exists --no-owner --exit-on-error < /PERCORSO-BACKUP/test.dump

Ripristinare i file TEST dello stesso punto temporale, riavviare e verificare.
Il solo dump non contiene le bozze. Non usare questi comandi su PROD.

Backup della migrazione:
/opt/asc/wms/backups/database-integration/test-20260921T234540.
Il container asc-wms-test-before-postgres-20260921T234540 conserva il backend
precedente. Riavviarlo torna al passato: non recupera modifiche SQL successive.

## Lezioni della migrazione

- Arrestare le scritture e confrontare identità, appartenenze e contenuti delle
  pratiche prima/dopo; non limitarsi ai conteggi.
- La normalizzazione legacy delle assegnazioni può cambiare il vecchio campo
  assignee: analizzare ogni differenza, senza accettare cambiamenti inspiegati.
- Rinominare un container non cancella le etichette Compose. Inventariare anche
  quelli fermi: Compose può ricreare un container storico dello stesso servizio.
- Clone/restore del pannello copiano JSON/pickle e non SQL: non usarli su TEST
  fino all'adeguamento.

## Verifiche sul server

Backend con directory isolata:

    WMS_DATA_DIR=$(mktemp -d) python3 -m unittest discover -s tests -v

Non impostare la URL del TEST operativo per test che scrivono dati.
I test PostgreSQL specifici creano schemi isolati e li eliminano a fine prova.

Angular con l'immagine strumenti già presente sul server:

    docker run --rm --user "$(id -u):$(id -g)" -e CHROME_BIN=/usr/local/bin/chrome-test -e NG_BUILD_MAX_WORKERS=2 -v "$PWD/frontend-angular:/work" -w /work asc-wms:graph-test-tools node node_modules/@angular/cli/bin/ng.js test --watch=false --browsers=ChromeHeadless

Per ricostruire strumenti equivalenti servono Node compatibile con Angular 20,
Chromium e lanciatore headless adatto al container. L'immagine strumenti è
distinta da quella applicativa.


La revisione è incorporata nell'immagine tramite WMS_REVISION e restituita da
/api/runtime. Testata e pannello mostrano la revisione installata, non l'HEAD
corrente del repository. Gli ambienti precedenti senza metadato mostrano nel
pannello l'identificativo immutabile dell'immagine, esplicitamente etichettato.


## Versione leggibile

Dal rilascio 1.4.2 revisione 1, backend/wms_web/version.py definisce VERSION e
REVISION per la testata e i pulsanti del pannello. Aggiornare questi valori per
i rilasci successivi. /api/runtime restituisce version e revision separati;
source_revision mantiene il riferimento tecnico al sorgente, non mostrato nei
pulsanti. Gli ambienti precedenti mostrano Versione non rilevata: non si ricava
una versione commerciale dal nome o dall'identificativo dell'immagine.
Questa convenzione sostituisce la precedente visualizzazione dei codici Git.

## Allineamento DEV / TEST / PROD — 22 settembre 2026

Tutti gli ambienti usano l'immagine asc-wms:1.4.2-r1 (Versione 1.4.2,
Revisione 1), con PostgreSQL 17 indipendenti sul solo server 192.168.11.10.
DEV e PROD sono copie iniziali dello snapshot TEST; non esiste replica continua.
Questa sezione sostituisce le precedenti indicazioni di persistenza legacy.

Configurazione completa da usare per i successivi rilasci:

    docker compose -f compose.yaml -f compose.database-test.yaml -f compose.database-environments.yaml up -d --no-build --no-deps wms-dev wms-test wms-prod

Eseguire solo per gli ambienti autorizzati. Non usare il solo compose.yaml:
i collegamenti ai database sono definiti negli override.

| Ambiente | Database e ruolo | Container | Volume persistente |
|---|---|---|---|
| DEV | wms_dev | asc-wms-dev-postgres | asc-wms-dev-postgres-data |
| TEST | wms_test | asc-wms-test-postgres | asc-wms-test-postgres-data |
| PROD | wms_prod | asc-wms-prod-postgres | asc-wms-prod-postgres-data |

I volumi risiedono in /var/lib/docker/volumes/NOME-VOLUME/_data sul server.
Ogni ambiente usa rete Docker e credenziali proprie; nessuna porta PostgreSQL
è pubblicata sull'host. File segreti: /opt/asc/wms/secrets/AMBIENTE-postgres.env
e AMBIENTE-database.env, permessi 600. Il PostgreSQL n8n resta indipendente.

Backup dell'allineamento: /opt/asc/wms/backups/align-environments-20260922T023806.
Contiene configurazioni precedenti, ispezioni container (riservate), dump TEST,
archivi completi dei tre ambienti e verifica delle tabelle. Sono preservati
utenti, password, gruppi, appartenenze, clienti, pratiche e repertori dello
snapshot TEST nelle due copie. Gli utenti preesistenti dei destinatari restano
nel backup precedente: non sono stati fusi con gli utenti TEST.

Le vecchie directory dati rimangono anche in
/opt/asc/wms/data/dev-before-20260922T023806 e
/opt/asc/wms/data/prod-before-20260922T023806.
Le vecchie immagini sono conservate come
asc-wms:dev-before-align-20260922T023806 e
asc-wms:prod-before-align-20260922T023806.

Ripristino al precedente ambiente legacy: fermare il solo destinatario,
salvare prima lo stato SQL e i file correnti, ripristinare la sua directory
precedente e avviarlo con l'immagine precedente e la configurazione salvata,
senza WMS_DATABASE_URL. Il ripristino torna al punto precedente al riversamento,
non incorpora le modifiche successive. Per ripristini SQL usare dump specifici
dell'ambiente e conservare anche le bozze su file.

Verifica: tutte le tabelle applicative DEV e PROD coincidono con lo snapshot
TEST; i tre runtime e gli endpoint health rispondono correttamente.
Il pannello offre ancora il controllo PostgreSQL specifico TEST; i vecchi
comandi di copia/ripristino solo file non sono adatti a questi ambienti SQL.
