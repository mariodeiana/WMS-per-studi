# Pannello di sistema — copia del servizio attivo

Indirizzo: http://192.168.11.10:8004.
Servizio: wms-management.service.
Sorgente attivo: /opt/asc/wms/management/management.py.
Questa copia conserva il codice verificato il 22 settembre 2026;
non viene distribuita automaticamente dal Dockerfile applicativo.

Funzioni presenti: stato DEV/TEST/PROD, riavvio singolo o complessivo,
DEV → TEST con precedente TEST salvato, ripristino TEST con scambio del punto
precedente. Sono operazioni su directory di file.

**Non usare clone/ripristino su TEST PostgreSQL:** manca pg_dump/pg_restore.
Il requisito dell'utente è PROD → TEST o DEV, con backup prima del riversamento
e ripristino: non è implementato nel servizio attivo.

Il servizio ascolta su 0.0.0.0:8004 senza autenticazione HTTP.
Non esporlo a Internet; un ampliamento degli accessi richiede autenticazione
e autorizzazioni. La pubblicazione non modifica servizio né accessi di rete.

Le varianti management-new.py e copie *.before-* restano sul server;
il riferimento versionato è il file effettivamente usato da systemd.

## PostgreSQL WMS TEST

La sezione PostgreSQL mostra stato container e disponibilità delle connessioni,
versione, dimensione database, tempo dall'avvio, connessioni totali e attive,
limite connessioni, clienti, pratiche, voci Repertorio, transazioni, rollback,
deadlock e tabelle più grandi. Le righe delle tabelle sono stime; i conteggi
applicativi sono esatti. Le statistiche cumulative riportano la data di reset.
Aggiornamento ogni 15 secondi, con comando manuale.

GET /api/postgres legge solo il database wms_test nel container
asc-wms-test-postgres. Un database fermo o una misura non disponibile non viene
mostrato come un valore zero e le vecchie misure vengono rimosse dalla pagina.

POST /api/postgres/restart opera solo sul PostgreSQL WMS TEST. Il pulsante chiede
conferma; arresta WMS TEST se in esecuzione, riavvia PostgreSQL, attende pg_isready
e riparte con WMS TEST per ristabilire la connessione persistente.
Un WMS TEST già fermo resta fermo; richieste di riavvio concorrenti sono rifiutate.
Il PostgreSQL di n8n non è coinvolto. Il controllo Riavvia tutte resta limitato
alle applicazioni WMS, non include PostgreSQL.

Verifiche: 7 test automatici con riavvio simulato, API e pagina HTTP reali,
misure lette dal PostgreSQL operativo. Nessun riavvio reale del database è stato
eseguito per collaudare il pulsante.
