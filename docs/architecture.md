# Architettura WMS

## Obiettivo

Costruire un Work Management System per studi professionali indipendente dal gestionale applicativo utilizzato.

## Modello concettuale

`Cliente -> Servizio -> Mandato -> Tipo di pratica -> Pratica -> Task`

Elementi trasversali: documenti, assegnazioni, scadenze, workflow, validazioni, audit log, riferimenti esterni.

## Regola di indipendenza

Il dominio WMS non contiene dipendenze obbligatorie verso GIS o altri gestionali. Le integrazioni avvengono tramite adapter/connector.

Schema logico:

`WMS Core <-> Connector/Adapter <-> Gestionale esterno`

## Oggetto centrale

La Pratica è l'istanza concreta di lavoro relativa a un cliente e a un periodo/evento. Nasce da un Tipo di pratica e genera i Task previsti dal relativo template.

## Stati iniziali della pratica

- DA_FARE
- IN_LAVORAZIONE
- COMPLETATA
- DA_VALIDARE
- VALIDATA
- CHIUSA

Il motore dovrà impedire transizioni non ammesse e registrare ogni transizione nell'audit log.

## Milestone v0.1

Caso pilota: `LIPE_TRIM`.

Flusso da dimostrare:

`Template -> Creazione pratica -> Generazione task -> Lavorazione -> Completamento -> Validazione -> Chiusura -> Audit`
