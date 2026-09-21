# Frontend Angular WMS

Frontend di destinazione del WMS; Python mantiene API, workflow, autenticazione
ed autorizzazioni. Il frontend precedente resta in `../frontend/` come riferimento.

Sul server ASC-OLB-WFO-01:

```sh
cd /opt/asc/wms/WMS-per-studi/frontend-angular
npm ci
npm start -- --host 0.0.0.0 --port 4200 --proxy-config proxy.conf.json
```

Aprire `http://192.168.11.10:4200`. Il proxy inoltra `/api` al solo backend DEV
sulla porta 8000. Non cambiare il proxy verso TEST (8001) o PROD (8002).

```sh
npm run build
npm test -- --watch=false --browsers=ChromeHeadless
```

Senza Chrome installato sul server: `npm test -- --watch=false --no-browsers`,
poi aprire la porta Karma 9876 con un browser tramite tunnel SSH.

La navigazione dipende dal ruolo attivo: Supervisore, Operatore, Validatore,
Amministratore. Il cambio appartenenza è disponibile nella barra superiore.
Le sessioni usano il cookie HttpOnly del backend, senza token nel localStorage.

Copertura, API e procedura di verifica isolata: [migrazione Angular](../docs/angular-migration.md).

Il grafo interattivo e il designer dei Tipi pratica usano Foblex Flow.
Istruzioni: [workflow a grafo](../docs/workflow-grafo.md#grafo-interattivo-angular).
