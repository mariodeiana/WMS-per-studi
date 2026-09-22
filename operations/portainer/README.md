# Portainer Community Edition

Server: 192.168.11.10. Accesso: https://192.168.11.10:9443.
Container asc-portainer, volume persistente asc-portainer-data.
L'immagine ufficiale LTS è bloccata al digest riportato in compose.yaml.

    docker compose -p asc-portainer -f operations/portainer/compose.yaml up -d

Il socket Docker permette di amministrare i container di questo server.
Portainer usa HTTPS con certificato autofirmato iniziale. Nessuna porta HTTP
9000 o Edge 8000 è pubblicata; la porta 8000 resta a WMS DEV.
La prima configurazione richiede il token iniziale dai log e la scelta della
password amministratore da parte dell'utente. Token e password non vanno in Git.
Il setup iniziale scade dopo cinque minuti: se necessario riavviare soltanto
asc-portainer e recuperare il token corrente dai log.

Dopo l'accesso scegliere l'ambiente Docker locale. Le applicazioni esistenti
restano gestite dai rispettivi file Compose; non ricrearne gli stack da Portainer
senza prima considerare configurazioni, dati e procedure di rilascio.

Backup di Portainer: arrestare solo asc-portainer, archiviare il suo volume,
riavviarlo. Questo salva la configurazione del pannello, non i database WMS:
i loro backup restano separati.
