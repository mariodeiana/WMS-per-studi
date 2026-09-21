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
