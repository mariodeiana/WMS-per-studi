# Stato verificato e decisioni — 22 settembre 2026

## Cliente e contratto

Il Cliente WMS è autonomo dall'anagrafica GIS. La scheda gestisce codice interno,
ragione sociale, codice fiscale, partita IVA, email, codice azienda GIS, regime
contabile, tipo liquidazione IVA, stato e note. Non sono definiti protocolli
di accesso a GIS, sincronizzazione o sistema master dei singoli campi.

Il Repertorio è la relazione Cliente ↔ Tipo pratica, con chiave composta e
riferimenti SQL. Esprime inclusione nel contratto e destinazione alla generazione
automatica. Non impedisce la creazione manuale fuori contratto.

Alla creazione la pratica registra separatamente origine AUTOMATICA/MANUALE e
regime IN_REPERTORIO/EXTRA_CONTRATTO, determinato dal server. Modifiche successive
al Repertorio non riscrivono queste informazioni. Lo storico conserva NULL
quando il dato non era rilevato. Non attribuire contratti retroattivamente.

La generazione automatica via API considera clienti e tipi attivi ed evita
duplicati automatici per cliente, tipo e periodo. Il pianificatore periodico
non è attivato. La creazione manuale rimane indipendente.

## Workflow e organizzazione

Il workflow resta un grafo orientato. I nodi iniziali sono espliciti, gli esiti
determinano le transizioni, più destinazioni attivano rami paralleli. L'ordine
visivo e le coordinate del designer non determinano l'esecuzione.
La validazione controlla riferimenti, cicli e raggiungibilità.
Il completamento riguarda i nodi raggiunti, non tutti i nodi indiscriminatamente.

Il designer conserva bozze recuperabili sul server; pubblicare il modello è
distinto dal salvataggio della bozza. Le bozze restano su file.
Gruppi, colori, appartenenze e separazione tra gruppo responsabile e operatore
incaricato sono mantenuti. La migrazione conserva anche gli hash delle password.

## Persistenza e migrazione TEST

TEST usa PostgreSQL 17 dedicato, separato da n8n.
Lo schema contiene relazioni per il Repertorio e payload JSON per diversi
aggregati: non è una normalizzazione completa del dominio.
Il codec tipizzato conserva task, risultati, evidenze, avanzamento e audit.
Il vecchio pickle è letto solo per importare lo storico.

L'importazione usa marcatori distinti per configurazione e pratiche; ripeterla
non duplica i dati. SQL è attivato soltanto con WMS_DATABASE_URL esplicita.
DEV e PROD restano legacy.

Al passaggio iniziale sono stati verificati 4 utenti, 5 gruppi, 6 appartenenze,
13 clienti, 4 tipi pratica e 15 pratiche. Sono valori della migrazione, non
invarianti futuri. Il Repertorio non è stato popolato inventando contratti.
Record e hash degli utenti non sono pubblicati.

Il backend mantiene lo stato in memoria: usare un solo processo per ambiente.
I lock proteggono richieste nello stesso processo, non più worker indipendenti.

## Collaudo e correzione visuale

Migrazione: 92 test backend, 46 Angular e 7 specifici PostgreSQL sul server.
Il 22 settembre Safari mostrava solo l'intestazione della finestra Cliente.
La presenza dei controlli nell'albero accessibile non dimostrava la visibilità.
La correzione assegna un'altezza alla finestra Cliente e una base automatica
agli elementi flex, conservando lo scorrimento interno.
I 46 test Angular sono stati rieseguiti, controllando anche i rettangoli visibili
di tab e campi. La conferma visiva finale in Safari resta da effettuare.

## Lavoro aperto

- Adeguare il pannello a backup/ripristino PostgreSQL più bozze su file e a
  riversamenti PROD → TEST/DEV, con backup del destinatario.
- Il pannello attivo offre DEV → TEST e ripristino TEST su file: non soddisfa
  ancora il requisito PROD → TEST/DEV né il nuovo SQL.
- Definire e attivare il pianificatore della generazione quando richiesto.
- Verificare l'accesso GIS prima di progettare connettori.
- Pianificare separatamente eventuali migrazioni DEV/PROD.
- Risolvere la sincronizzazione dello stato prima di introdurre più worker.
