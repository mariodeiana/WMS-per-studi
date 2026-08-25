# Roadmap funzionale WMS v0.2 -> v0.6

## Principio guida

Il WMS codifica il metodo di lavoro dello studio. Deve stabilire cosa fare, chi deve farlo, entro quando, con quali istruzioni, quali evidenze produrre e quale lavoro ha priorità. Le integrazioni con gestionali esterni restano opzionali e avvengono tramite connector/adapter.

## v0.2 — Work Distribution & Roles

Stato: prototipo funzionante.

Obiettivi:
- Task assegnabili a uno specifico operatore.
- Work Queue personale dell'operatore.
- Task eseguibili fuori ordine salvo dipendenze esplicite.
- Ruoli distinti: OPERATORE, VALIDATORE, MANAGER.
- Separazione dei compiti: chi ha eseguito task della pratica non può validarla.
- Validazione e chiusura separate dall'esecuzione operativa.
- Scheda Pratica Manager con visione complessiva, assegnazioni, avanzamento e audit.

## v0.3 — Work Results & Evidence

Obiettivi:
- Ogni attività significativa produce un risultato strutturato.
- Task operativo: esito, nota, allegati/evidenze, autore, data/ora.
- Validazione: esito, nota, allegati/evidenze, validatore, data/ora.
- Chiusura: esito finale, nota, allegati/evidenze, manager, data/ora.
- Distinzione netta fra Audit e Fascicolo/Evidenze.
- Manager e Validatore possono consultare note ed evidenze prodotte dai task.
- Base del Task Context: il singolo task espone in modo chiaro istruzioni, contesto pratica e risultati precedenti disponibili.

## v0.4 — Portfolio, Schedule & Priority Engine

Obiettivi:
- Dashboard/Portafoglio Pratiche come home del WMS.
- Pratiche aperte in evidenza e organizzabili per stato, cliente, tipo, operatore, scadenza e priorità.
- Schedule Policy relativa alla scadenza finale X.
- Milestone configurabili nel template, ad esempio: chiusura X-2, validazione X-3, task N/N X-4, task N-1/N X-6.
- Confronto continuo fra stato atteso e stato reale.
- Ritardo operativo espresso rispetto alla milestone attesa, non solo rispetto alla scadenza finale.
- Priority score dinamico basato almeno su scadenza, milestone, avanzamento reale, ritardo, blocchi, criticità e override manageriale.
- La stessa priorità alimenta Dashboard Manager e Work Queue Operatore.

## v0.5 — Operational Instructions & Context Engine

Obiettivi:
- Ogni Task Template deve contenere istruzioni operative chiare e sempre visibili all'operatore prima del completamento.
- Le istruzioni devono poter contenere marker contestuali del tipo `%%mail_amministrativa%%`, `%%mail_titolare%%`, `%%cliente_ragione_sociale%%`, `%%periodo_pratica%%`, `%%data_scadenza%%`.
- I marker vengono risolti da anagrafica cliente, dati pratica e in futuro da connector esterni.
- Un marker obbligatorio non risolto deve essere segnalato esplicitamente; il template può stabilire se il dato mancante blocca il task.
- Task Context = istruzioni risolte + dati cliente/pratica + evidenze delle fasi precedenti + documenti richiesti + scadenza operativa.
- Evoluzione successiva: document checklist per task, con documenti richiesti/obbligatori/facoltativi e propagazione delle evidenze alle fasi successive.

## v0.6 — Mail & Event-Driven Workflow

Obiettivi:
- Gestione della posta integrata nel WMS, non delegata necessariamente al client locale.
- Mail Composer con destinatari, oggetto, corpo e allegati contestualizzati tramite marker.
- Oggetti e header correlabili a Pratica + Task; conservazione di Message-ID, In-Reply-To e References.
- Mail Gateway per invio/ricezione tramite provider/API/SMTP-IMAP.
- Mail Correlation Engine per collegare risposte e allegati alla pratica corretta.
- Task automatici/event-driven che avanzano al verificarsi di eventi esterni.
- Stato generico `IN_ATTESA_ESTERNA` con motivi quali CLIENTE, ENTE, GESTIONALE, DOCUMENTO, FIRMA, PAGAMENTO.
- Esempio: invio F24 -> task in attesa cliente -> risposta ricevuta -> mail e allegati archiviati -> audit -> avanzamento workflow.
- Ogni automazione deve produrre eventi audit espliciti; nessun avanzamento silenzioso.

## Direzione di prodotto

Il WMS non deve limitarsi a registrare il lavoro svolto. Deve mettere l'operatore nelle condizioni di eseguire correttamente il lavoro, guidarlo con il metodo dello studio, conservare il risultato e le evidenze, coordinare passaggi di consegne, monitorare la traiettoria rispetto alle scadenze e determinare dinamicamente quale attività ha priorità in ogni momento.
