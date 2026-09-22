# WMS per studi

Sistema per governare clienti, tipi pratica, pratiche, attività, assegnazioni,
scadenze, risultati, documenti, validazioni e audit negli studi professionali.
La pratica è l'oggetto centrale; il workflow mantiene un grafo orientato.

## Regola operativa

**Sviluppo, test, produzione, database, build e backup esclusivamente sul server
ASC-OLB-WFO-01, 192.168.11.10.** Nessun ambiente o copia di lavoro locale.
Leggere [AGENTS.md](AGENTS.md) prima di operare.

| Ambiente | Indirizzo | Persistenza verificata il 22 settembre 2026 |
|---|---|---|
| DEV | http://192.168.11.10:8000 | PostgreSQL 17 dedicato |
| TEST | http://192.168.11.10:8001 | PostgreSQL 17 dedicato |
| PROD | http://192.168.11.10:8002 | PostgreSQL 17 dedicato |
| Pannello di sistema | http://192.168.11.10:8004 | Stato, riavvii e procedure legacy |

Repository sul server: /opt/asc/wms/WMS-per-studi.
Aggiornare TEST non aggiorna DEV o PROD.

## Punto di ingresso al know-how

- [Indice della documentazione](docs/README.md)
- [Stato attuale, decisioni e lavoro da completare](docs/stato-e-decisioni.md)
- [Operazioni, rilascio e ripristino](docs/operazioni-server.md)
- [PostgreSQL, migrazione e Repertorio](docs/database-repertorio.md)
- [Workflow a grafo e designer](docs/workflow-grafo.md)
- [Manuale operativo 1.4.1](docs/manuali/Manuale-WMS-1.4.1.md)
- [Pannello di sistema: codice e limiti](operations/management/README.md)

## Scheda Cliente

In TEST, scegliere **Amministratore → Configurazione → Clienti → Modifica**.
La finestra contiene **Anagrafica**, **Dati fiscali**, **REPERTORIO** e **Pratiche**.
Il Repertorio contiene i tipi compresi nel contratto. Le pratiche manuali fuori
repertorio restano consentite e sono extra contratto. Origine e regime economico
sono conservati al momento della creazione.

Il codice GIS è soltanto un riferimento esterno: nessuna integrazione è attiva.

## Struttura

backend/wms_core contiene il dominio; backend/wms_web contiene API,
autenticazione, configurazione e persistenza; backend/migrations contiene SQL.
frontend-angular è l'interfaccia distribuita; frontend conserva quella precedente.
tests e i file Angular *.spec.ts contengono le verifiche automatiche.

Il Dockerfile costruisce Angular con Node 20 e il backend con Python 3.13,
installando backend/requirements.txt. Build e test si eseguono sul server.

Il repository conserva codice e conoscenza tecnica. Credenziali, dati operativi,
database, allegati e backup restano sul server.
