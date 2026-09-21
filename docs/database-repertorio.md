# PostgreSQL e Repertorio cliente — ambiente TEST

Host: ASC-OLB-WFO-01, 192.168.11.10. Sviluppo, build e test solo remoti.
Il container asc-wms-test-postgres usa PostgreSQL 17, database wms_test e volume
persistente asc-wms-test-postgres-data. Non espone porte sul server: comunica
con TEST sulla rete Docker asc-wms-test-db. Il database n8n resta separato.
Le credenziali sono in /opt/asc/wms/secrets/test-database.env (permessi 600).

## Gestione TEST

```sh
docker compose -f compose.yaml -f compose.database-test.yaml up -d --no-build wms-test
```

L'override sceglie l'immagine con migrazione SQL e configura WMS_DATABASE_URL.
In assenza della variabile il backend mantiene la persistenza legacy; DEV e
PROD non sono migrati automaticamente. Un solo processo backend per ambiente:
lo stato è caricato in memoria e le richieste concorrenti sono gestite dai lock.

## Importazione e conservazione

Il comando backend.wms_web.migrate_database richiede una URL PostgreSQL esplicita
(--database oppure WMS_DATABASE_URL), salva i file JSON/pickle in un backup
prima dell'importazione e non modifica gli originali. Il DB usa marcatori per
importare configurazione e pratiche una sola volta, anche ripetendo il comando.
I file delle bozze dei modelli restano in /data/.wms-model-drafts e sono conservati.
Gli utenti, hash password, gruppi, colori e appartenenze vengono mantenuti.
Le pratiche sono serializzate in JSON tipizzato, con task, grafo, risultati,
evidenze, avanzamento e audit invariati. Gli ID restano quelli precedenti.

## Repertorio e pratiche

client_repertoire collega clients e practice_types con chiave composta e FK.
Il repertorio indica inclusione contrattuale e destinazione alla generazione
per clienti e tipi attivi. Non limita l'istanza manuale fuori contratto.

POST /api/admin/config/clients salva l'anagrafica e repertoire (lista ID dei tipi).
Campi: name, tax_code, vat_number, gis_company_code, accounting_regime,
vat_settlement_type, active, notes. GIS resta un semplice riferimento esterno.

POST /api/admin/practices crea MANUALE e determina sul server IN_REPERTORIO o
EXTRA_CONTRATTO. POST /api/admin/practices/generate genera AUTOMATICA per i clienti
in repertorio, senza duplicati per cliente/tipo/periodo, con salvataggio atomico.
Il pianificatore periodico non è ancora attivato. I controlli sul grafo e i nodi
iniziali espliciti rimangono operativi. Le modifiche al repertorio non alterano
le pratiche già istanziate. Per lo storico, origine e regime sono NULL/non rilevati:
non vengono inventate attribuzioni contrattuali retroattive.

La scheda Cliente Angular espone Anagrafica, Dati fiscali, Repertorio e Pratiche.

## Backup e ripristino

Prima del passaggio sono conservati codice, intera directory TEST e container
precedente sotto /opt/asc/wms/backups/database-integration. Per un backup nuovo:

```sh
docker exec asc-wms-test-postgres pg_dump -U wms_test -d wms_test -Fc > wms-test.dump
```

Conservare anche la directory /opt/asc/wms/data/test per le bozze e gli altri file.
Per un ripristino SQL fermare TEST, usare pg_restore nel database TEST e riavviare.
I vecchi riversamenti basati soltanto su JSON/pickle NON aggiornano il database SQL:
prima di usare il pannello di sistema con TEST va adattata anche quella procedura.
Il ritorno immediato precedente alla migrazione usa il container fermato conservato
come asc-wms-test-before-postgres-*; non recupera le modifiche effettuate dopo il passaggio.

Collaudo: 92 test backend, 46 test Angular e 7 test specifici PostgreSQL sul server.
