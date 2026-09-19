# Migrazione Angular — 19 settembre 2026

## Checkpoint e architettura

Checkpoint iniziale: `a318e6b36ed2f2d4dcf37c42c4d4358136d5905d`, branch
`dev/session-28-aug-login-role`. Include lo spin-off Manager e la separazione
`client_id` / `client_name`, verificati con 54 test backend e build Angular.

La working tree di riferimento è su ASC-OLB-WFO-01:
`/opt/asc/wms/WMS-per-studi`. Angular è il frontend di destinazione.
Python conserva autenticazione, autorizzazioni, assegnazioni, persistenza,
workflow, validazione, non conformità e audit. I controlli nel browser sono
solo presentazione e compilazione dei moduli; il backend verifica le operazioni.

## Copertura delle interfacce

| Interfaccia precedente | Percorso Angular | Funzioni migrate |
| --- | --- | --- |
| login.html / auth-context.js | /login e barra comune | Accesso, sessione, cambio appartenenza, logout, gestione 401/403 e rete |
| index.html | /manager | KPI, elenco ordinato dal backend, cliente/codice, accesso alla pratica |
| practice.html | /practices/:id | Attività, gruppi, risultati, fascicolo, audit, chiusura |
| manager-task.html | /practices/:id/tasks/:code | Dettaglio, istruzioni, risultato corrente e storico, riapertura motivata |
| queue.html | /work | Attività operative, riaperte, in corso e completate recenti |
| task.html | /work/:id/:code | Istruzioni, esiti configurati, note, salvataggio intermedio, completamento, diario, risultati ed evidenze |
| validation-list.html | /validation | Coda e storico personale delle ultime 8 ore |
| validation.html | /practices/:id con ruolo Validatore | Esiti, motivazione, allegati, verifica NC e correzioni |
| NC e azioni correttive | Dettaglio pratica | Stato e storico dal backend, selezione task, istruzioni di correzione |
| configuration.html | /admin | CRUD utenti/gruppi/appartenenze/politiche/clienti/modelli; creazione e consultazione pratiche |
| Editor modelli | /admin → Tipi di pratica | Attività, ordinamento, gruppi, scadenze, istruzioni, dipendenze, esiti e transizioni |

I file di `frontend/` restano invariati come riferimento. Non sono rimossi dal repository; dal rilascio del 19 settembre 2026
Angular è il frontend dei servizi DEV, TEST e PROD. La creazione di utenti non imposta una
password: resta il comportamento del backend esistente e della vecchia UI.
Il ruolo DECISORE non dispone ancora di una propria interfaccia operativa nel
frontend precedente; Angular presenta il selettore di contesto.

## Estensioni API additive

- `GET /api/manager/assignment-groups`: soli gruppi Operatore attivi, accessibile
  al Manager; la riassegnazione verifica sul server l'esistenza del gruppo.
- Dettaglio pratica: `nonconformities` espone lo stato e le azioni correttive
  già presenti nel dominio, senza ricostruirli nel browser dall'audit.
- Dettaglio task con `context=1`: `task_results` espone i risultati del task,
  compreso lo storico; i precedenti risultati degli altri task restano separati.

## Verifica riproducibile

Backend, sempre con dati temporanei separati:

```sh
task_test_dir=$(mktemp -d /tmp/wms-tests.XXXXXX)
WMS_DATA_DIR="$task_test_dir" WMS_ENV=DEV python3 -m unittest discover -s tests -v
```

Angular:

```sh
cd frontend-angular
npm run build
npm test -- --watch=false --browsers=ChromeHeadless
```

Se sul server manca Chrome, usare `npm test -- --watch=false --no-browsers`
e collegare un browser a Karma (porta 9876) tramite tunnel SSH.

Prova integrata con dati usa e getta, eseguita sul server e non sui dati DEV:

```sh
python3 tools/angular_preview.py
```

Il processo ascolta solo su `127.0.0.1:8765` del server. Per aprirlo dal Mac:

```sh
ssh -N -L 8765:127.0.0.1:8765 ASC-OLB-WFO-01
```

La porta locale è un tunnel verso il server, non uno spostamento del WMS sul Mac.
Alla chiusura ordinata dell'anteprima i dati temporanei vengono eliminati.

## Accettazione

Verificato nel browser con dati sintetici: login; cambio Manager/Amministratore/
Operatore; creazione e modifica cliente; creazione modello con esito configurato;
creazione pratica; salvataggio intermedio con allegato e descrizione; ripresa e
completamento; login di un Validatore distinto; rifiuto senza motivazione bloccato;
non conformità; azione correttiva; nuovo completamento; nuova validazione;
NC chiusa; chiusura Manager; risultati e storico conservati.

La rimozione del frontend precedente richiede una revisione di accettazione
su casi rappresentativi dello studio; non è parte di questo passaggio tecnico.

Risultato delle verifiche automatiche del blocco migrato: **57 test backend** e
**16 test Angular** superati; build Angular di produzione completata senza
avvisi. I test Angular comprendono il ciclo di sessione, errori di rete e 401,
editor di modelli e riferimenti delle transizioni, mantenimento dei dati dopo
un errore del server, moduli incompleti e caricamento degli allegati.

## Revisione interfacce e palette Manager

Configurazione e dettaglio pratica/attività riprendono la palette della Scrivania
Manager: blu scuro, bianco, grigi chiari e accenti oro. Gli stati operativi
mantengono colori semantici. La configurazione usa finestre modali con intestazione
e comandi fissi, schede per dati generali/attività, attività espandibili e ricerca
nelle anagrafiche. Il dettaglio pratica separa attività, azioni e fascicolo a schede;
risultati, documenti e allegati condividono componenti più compatti.

Verificati nel browser sull'anteprima con dati temporanei: apertura/modifica modello,
cambio scheda senza perdita dei dati, espansione attività, salvataggio e riapertura
attività dal dettaglio Manager con conservazione del risultato nello storico.
Confermati 57 test backend, 16 test Angular e build di produzione senza avvisi.
Questo blocco riguarda configurazione, dettaglio e componenti condivisi; la revisione
visiva completa delle scrivanie Operatore/Validatore resta da completare.


## Rilascio su DEV, TEST e PROD

Il Dockerfile compila Angular con npm ci e include il bundle nella stessa immagine
Python. Le API e i dati restano nei rispettivi ambienti. WMS_FRONTEND=angular è
il valore predefinito dell'immagine; il sorgente eseguito direttamente conserva
legacy come default per compatibilità. WMS_ANGULAR_DIR permette di indicare un
bundle alternativo. Il frontend mostra l'ambiente ricevuto da /api/runtime.

Le porte restano DEV 8000, TEST 8001, PROD 8002. La porta 4200 resta il server
di sviluppo Angular con aggiornamento automatico verso le API DEV.
I vecchi link HTML reindirizzano ai percorsi Angular. Le API non autenticate
mantengono il rifiuto 401; il fallback SPA non intercetta le API o gli asset mancanti.

Prima del rilascio: 64 test backend, 19 test Angular, build Docker e prova
su copie coerenti dei tre archivi, con verifica di pratiche, stati, risultati,
evidenze e conteggi configurazione. I tre servizi vengono aggiornati in sequenza
promuovendo la stessa immagine, senza ricompilazioni differenti tra ambienti.

Backup del passaggio: /opt/asc/wms/backups/angular-20260919-181852.
manifest.json contiene immagini precedenti e tag rollback; i tar conservano
gli archivi. Ogni ambiente ha anche un backup immediatamente precedente al
proprio aggiornamento, creato a servizio arrestato.
Per ripristinare il software: riassegnare il rollback_tag del manifest al tag
asc-wms:dev, :test o :prod e ricreare solo il servizio interessato con
docker compose up -d --no-build --no-deps wms-<ambiente>.
Il ripristino dei dati da tar è una procedura separata: valutare e conservare
prima le operazioni avvenute dopo il rilascio. Non sovrascrivere dati successivi
automaticamente. Il riavvio richiede un nuovo accesso degli utenti.
