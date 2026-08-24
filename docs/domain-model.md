# Modello di dominio

## Entità principali

### Cliente
Soggetto per il quale lo studio svolge il lavoro.

### Servizio
Area di servizio erogata dallo studio.

### Mandato
Legame tra Cliente e Servizi affidati allo studio.

### Tipo di pratica
Definizione riutilizzabile di un lavoro ricorrente o specifico.

### Pratica
Istanza concreta di un Tipo di pratica per un Cliente e un periodo/evento.

### Task
Singola attività operativa all'interno di una Pratica.

### Template di task
Definizione dei Task che devono essere generati quando nasce una Pratica.

### Documento
Documento collegato alla Pratica e/o a un Task.

### Audit Event
Evento immutabile che registra creazione, assegnazione, cambio stato, completamento, validazione e altre operazioni significative.

### External Reference
Collegamento non vincolante tra un'entità WMS e un identificativo presente in un sistema esterno.

Campi concettuali minimi:

- entity_type
- entity_id
- system
- external_id
- external_code
- metadata

Esempi di `system`: GIS, TEAMSYSTEM, ZUCCHETTI, SISTEMI.

## Regole iniziali

1. Una Pratica deve appartenere a un Cliente.
2. Una Pratica deve derivare da un Tipo di pratica.
3. La creazione della Pratica materializza i Task previsti dal template.
4. Il completamento di tutti i Task non implica necessariamente la chiusura della Pratica.
5. Se il Tipo di pratica richiede validazione, la Pratica passa a `DA_VALIDARE`.
6. Solo un ruolo autorizzato può validare.
7. Ogni cambio di stato produce un Audit Event.
