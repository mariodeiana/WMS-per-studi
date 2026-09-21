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
