# WMS per studi

Work Management System indipendente dai gestionali applicativi, progettato per governare il metodo di lavoro degli studi professionali.

## Principio fondante

Il WMS governa clienti, mandati, tipi di pratica, pratiche, task, scadenze, assegnazioni, documenti, workflow, validazioni e audit. I gestionali esterni (GIS, TeamSystem, Zucchetti, Sistemi, altri) sono integrati tramite connettori dedicati e non costituiscono una dipendenza strutturale del core.

## WMS Core v0.1

Caso pilota: `LIPE_TRIM`.

Obiettivo end-to-end:

`Template -> Pratica -> Task -> Workflow -> Validazione -> Audit`

Oggetto centrale del sistema: **Pratica**.

## Web app locale: Scheda Pratica LIPE_TRIM

La web app usa esclusivamente la libreria standard Python e applica le azioni al
dominio `WMS Core` esistente. Lo stato è mantenuto in memoria per questa
iterazione dimostrativa: riavviare il processo ripristina la pratica di esempio.

Requisito: **Python 3.10 o successivo**. Dalla radice del repository eseguire:

```bash
python3 -m backend.wms_web.app
```

Aprire quindi **http://127.0.0.1:8000/** nel browser. La pagina mostra la Scheda
Pratica `LIPE_TRIM` e consente di completare i sette task, validare la pratica,
chiuderla e consultare l'audit log. Per usare un'altra porta:

```bash
python3 -m backend.wms_web.app --port 8080
```

### Test

Non sono necessarie dipendenze da installare. Dalla radice del repository:

```bash
python3 -m unittest discover -s tests -v
```
