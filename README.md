# WMS per studi

Work Management System indipendente dai gestionali applicativi, progettato per governare il metodo di lavoro degli studi professionali.

## Principio fondante

Il WMS governa clienti, mandati, tipi di pratica, pratiche, task, scadenze, assegnazioni, documenti, workflow, validazioni e audit. I gestionali esterni (GIS, TeamSystem, Zucchetti, Sistemi, altri) sono integrati tramite connettori dedicati e non costituiscono una dipendenza strutturale del core.

## WMS Core v0.1

Caso pilota: `LIPE_TRIM`.

Obiettivo end-to-end:

`Template -> Pratica -> Task -> Workflow -> Validazione -> Audit`

Oggetto centrale del sistema: **Pratica**.

## WMS v0.2: demo operativa LIPE_TRIM

La web app usa esclusivamente la libreria standard Python e applica le azioni al
dominio `WMS Core` esistente. Lo stato è mantenuto in memoria per questa
iterazione dimostrativa: riavviare il processo ripristina la pratica di esempio.

Requisito: **Python 3.10 o successivo**. Dalla radice del repository eseguire:

```bash
python3 -m backend.wms_web.app
```

Aprire quindi:

- **http://127.0.0.1:8000/** per la Scheda Pratica Manager: assegnazioni,
  avanzamento, autori dei completamenti, audit, riapertura e chiusura;
- **http://127.0.0.1:8000/queue.html?operator=anna.operatore** per la Work Queue
  di Anna;
- **http://127.0.0.1:8000/queue.html?operator=luca.operatore** per la Work Queue
  di Luca;
- **http://127.0.0.1:8000/validation.html** per la vista del validatore.

Le identità demo sono `anna.operatore` e `luca.operatore` (`OPERATORE`),
`valeria.validatore` (`VALIDATORE`) e `marta.manager` (`MANAGER`). I sette task
LIPE sono distribuiti tra i due operatori e sono indipendenti: l'ordine nel
template è solo grafico; eventuali dipendenze sono dichiarate esplicitamente.
La separazione dei compiti impedisce a chi ha completato un task di validare la
stessa pratica. Per usare un'altra porta:

```bash
python3 -m backend.wms_web.app --port 8080
```

### Test

Non sono necessarie dipendenze da installare. Dalla radice del repository:

```bash
python3 -m unittest discover -s tests -v
```
