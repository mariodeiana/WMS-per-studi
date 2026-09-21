# Regola universale del progetto WMS per studi

Per disposizione esplicita dell'utente, gli unici ambienti di sviluppo, TEST e
produzione sono quelli del server ASC-OLB-WFO-01, indirizzo 192.168.11.10.

- DEV: http://192.168.11.10:8000
- TEST: http://192.168.11.10:8001
- PROD: http://192.168.11.10:8002
- Repository: /opt/asc/wms/WMS-per-studi

Tutto il lavoro applicativo deve avvenire sul server: sviluppo, modifiche al
codice, installazioni, database, build, test, anteprime, processi, dati e backup.
Non creare né mantenere sul Mac o su altre macchine copie di lavoro, ambienti,
database, runtime, dipendenze o servizi del WMS. Il computer locale può essere
usato soltanto come client SSH/browser per accedere al server.

Se il server non è raggiungibile, fermare il lavoro applicativo e segnalare il
problema: non installare o avviare un ambiente locale come alternativa.

DEV, TEST e PROD sono separati. Operare soltanto sugli ambienti inclusi nella
richiesta. Prima di migrazioni o riversamenti salvare un backup ripristinabile,
preservare utenti/gruppi/appartenenze e verificare i dati dopo l'operazione.

La regola vale per tutte le sessioni e tutti gli agenti del progetto. Una
modifica richiede una nuova indicazione esplicita dell'utente.
