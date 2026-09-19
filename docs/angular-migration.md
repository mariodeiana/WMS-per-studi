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

I file di `frontend/` restano invariati come riferimento. Non sono rimossi
né sostituiti nei servizi TEST e PROD. La creazione di utenti non imposta una
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
