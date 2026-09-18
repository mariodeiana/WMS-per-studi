# Sessione 14 settembre 2026 — correzione allegati e revisione funzionale

Repository: /Users/mario/Documents/WMS-per-studi. Branch: dev/session-28-aug-login-role.

## Download automatico in F24-04

Riproduzione confermata nella demo originale su 8000: il materiale precedente della pratica P-2026-F24-002 identifica E-0003 come P-2026-F24-002-F24-03-parziale.txt, ma GET /api/evidence/E-0003?disposition=inline restituisce incontro preliminare.odt, MIME application/vnd.oasis.opendocument.text.

Gli ID delle evidenze sono progressivi dentro ogni pratica. Il servizio cercava il primo ID corrispondente in tutte le pratiche. La scheda operatore, usando il MIME del TXT, inseriva un iframe con src già impostato dentro il popover nascosto. Il browser caricava quindi un ODT di un'altra pratica senza alcuna azione dell'utente.

La correzione aggiunge la pratica a preview_url e download_url e limita la ricerca alla pratica indicata. I vecchi link senza pratica continuano a funzionare quando l'ID è univoco; quelli ambigui restituiscono 404. Non occorre migrare ID, risultati o allegati persistenti. Le anteprime integrate di immagini, PDF e testo vengono caricate dal pulsante Mostra anteprima. I collegamenti di apertura restano disponibili anche per documenti non visualizzabili dal browser. Disposizioni inline/attachment e contenuti sono invariati.

## Verifica

- Suite Python: 32 test superati. Test HTTP aggiornati dal vecchio modello actor/assegnatario a sessione autenticata, ruolo e gruppo. Verificati rifiuto di actor falsificati e claim di altro operatore.
- Regressione: due pratiche con stesso ID restituiscono ciascuna i propri byte, MIME e filename sia per anteprima sia per download; pratica inesistente e ID ambiguo restituiscono 404; link precedente univoco funzionante.
- Demo corretta su 8001, con copia dello stato persistente e configurazione temporanea: apertura F24-04, tre iframe senza src al caricamento, src impostato solo dopo Mostra anteprima e relativo alla pratica F24 corretta.
- CRUD delle cinque entità su dati temporanei: creazione, lettura, aggiornamento/disattivazione ed eliminazione completati.
- Cambio Manager → Operatore Contabili → Amministratore senza nuovo login verificato nel browser. Modulo Nuovo e navigazione Tipi di pratica disponibili.

La demo originale su 8000 non è stata interrotta: deve essere riavviata per caricare la correzione Python. Le modifiche alla demo di verifica non toccano i dati persistenti dell'utente.

## Revisione funzionale dal 28 agosto

1. Le cinque tabelle di configurazione hanno CRUD persistente, riservato al ruolo Amministratore. Il ruolo compare fra le tre appartenenze di Mario Demo.
2. Le configurazioni organizzative non alimentano ancora l'autenticazione: auth.py usa DEMO_ACCOUNTS e GROUPS statici. Creare/disattivare utenti, gruppi o appartenenze nella configurazione non modifica l'accesso operativo della demo.
3. Tipi di pratica contiene il solo record LIPE; i cinque modelli realmente usati sono definiti in backend/wms_core/templates.py: LIPE_TRIM (7 task), F24_MENSILE (5), RICONC_BANCA (5), CU_ANNUALE (6), BILANCIO_VER (6). Il CRUD practice_types non modifica questi modelli e non espone i task associati.
4. La scrivania Manager mostra le 25 pratiche demo, cinque clienti e cinque tipi. La scheda pratica usa ancora task.assignee, rimosso dalla risposta organizzativa: appare undefined e il selettore propone Anna/Luca, mentre l'API richiede un gruppo. Questo disallineamento richiede una correzione funzionale separata.
5. Le code operatore sono filtrate per gruppo e claim; i test coprono completamento, evidenze, riapertura, ricompletamento, validazione e chiusura con ruoli autenticati.

Prossimo intervento funzionale: allineare la scheda Manager alle assegnazioni per gruppo; unificare configurazione e directory operativa; rendere consultabili e poi configurabili i task di ciascun modello pratica. Queste estensioni non sono incluse nella correzione del download.
