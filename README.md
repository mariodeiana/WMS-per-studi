# WMS per studi

Work Management System indipendente dai gestionali applicativi, progettato per governare il metodo di lavoro degli studi professionali.

## Principio fondante

Il WMS governa clienti, mandati, tipi di pratica, pratiche, task, scadenze, assegnazioni, documenti, workflow, validazioni e audit. I gestionali esterni (GIS, TeamSystem, Zucchetti, Sistemi, altri) sono integrati tramite connettori dedicati e non costituiscono una dipendenza strutturale del core.

## WMS Core v0.3

Caso pilota: `LIPE_TRIM`.

Obiettivo end-to-end:

`Template -> Pratica -> Task -> Workflow -> Validazione -> Audit`

Oggetto centrale del sistema: **Pratica**.

La v0.3 aggiunge risultati strutturati per completamento, validazione e chiusura,
evidenze raccolte nel fascicolo della pratica e rappresentazioni API indipendenti
dal framework per Work Queue, Scheda Task, vista Validatore e Scheda Manager.
Audit (evento) e fascicolo (contenuto di lavoro) rimangono oggetti separati.

## Avvio locale

Il progetto usa soltanto la libreria standard Python. Dalla root del repository,
la web app completa si avvia con:

```bash
python3 -m backend.wms_web.app
```

Aprire `http://127.0.0.1:8000`. Per eseguire la suite:

```bash
python -m unittest discover -s tests -v
```
