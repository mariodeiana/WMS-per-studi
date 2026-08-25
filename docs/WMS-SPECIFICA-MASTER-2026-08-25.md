# WMS per studi — Specifica Master consolidata

Data consolidamento: 25 agosto 2026

Questo documento conserva le decisioni funzionali e di interfaccia maturate durante la progettazione delle versioni v0.2-v0.6 e deve essere considerato riferimento prima di ulteriori implementazioni. Non rappresenta l'accettazione delle PR sperimentali successive: descrive il prodotto desiderato.

## 1. Principio generale

Il WMS deve essere gestionale-agnostico. Il metodo operativo appartiene al WMS, ai Template di Pratica e ai Task, non alla memoria delle persone e non a uno specifico gestionale esterno.

Il sistema deve guidare l'utente nell'esecuzione corretta del lavoro, conservare evidenze e tracciabilità, separare i ruoli e permettere future integrazioni.

## 2. Ruoli e separazione dei compiti

Ruoli principali:

- OPERATORE: esegue i Task assegnati.
- VALIDATORE: controlla il lavoro prodotto e valida la pratica.
- MANAGER: governa portafoglio, assegnazioni, eccezioni, riaperture e chiusura.

Il completamento di un Task non equivale alla validazione. La validazione non equivale alla chiusura. La validazione e la chiusura devono competere a soggetti/ruoli appropriati e deve essere preservata la separazione dei compiti, incluso il divieto di autovalidazione quando previsto.

## 3. Modello Pratica e Task

Una Pratica deriva da un Template di Pratica ed è composta da Task.

I Task possono essere eseguiti anche non nell'ordine numerico del template, salvo dipendenze esplicite. Ogni Task è assegnabile a uno specifico operatore.

La pratica deve consentire almeno stati coerenti con il ciclo: DA_FARE, IN_LAVORAZIONE, DA_VALIDARE, VALIDATA, CHIUSA, oltre a stati futuri come IN_ATTESA_ESTERNA.

Il Manager deve poter riaprire un Task quando necessario, con tracciamento dell'azione.

## 4. Work Queue Operatore

L'Operatore non deve vedere come superficie principale tutti i Task della pratica. Deve avere una Work Queue personale contenente le attività assegnate a lui.

Ogni elemento deve mostrare almeno:

- priorità/urgenza;
- cliente;
- pratica/tipo pratica;
- Task;
- scadenza operativa del Task o milestone;
- scadenza finale della pratica;
- eventuale ritardo;
- dipendenze o blocchi;
- stato sintetico.

L'ordinamento predefinito deve essere per priorità operativa, non per ordine numerico del template.

Dopo il completamento di un Task l'Operatore deve ritornare automaticamente alla propria Work Queue.

## 5. Scheda Task Operatore

È la schermata centrale del lavoro quotidiano.

Gerarchia informativa:

1. cosa devo fare;
2. cliente e pratica;
3. scadenza e priorità;
4. istruzioni operative sempre ben visibili;
5. contesto necessario della pratica e del cliente;
6. dipendenze;
7. materiale/documenti/evidenze provenienti dalle fasi precedenti;
8. documenti richiesti per il Task;
9. area risultato del lavoro;
10. comando Completa attività.

Le istruzioni operative devono provenire dal Template/Task e non essere hard-coded nella pagina. Chi progetta la pratica deve poter scrivere istruzioni chiare che l'operatore deve seguire prima di dichiarare il Task eseguito.

## 6. Risultato di lavoro

Ogni azione significativa deve produrre un risultato strutturato distinto dall'audit.

Campi concettuali minimi:

- actor;
- actor_role;
- timestamp;
- outcome/esito;
- note;
- attachments/evidence;
- related_practice_id;
- related_task_code quando pertinente.

Task, Validazione e Chiusura devono poter contenere nota, esito e allegati/evidenze.

## 7. Evidenze e fascicolo

Le evidenze appartengono alla Pratica e possono originare da Task, Validazione, Chiusura o eventi esterni.

Il fascicolo deve essere distinto dall'audit:

- Audit = cosa è successo, chi e quando.
- Fascicolo/Evidence Store = contenuto prodotto o ricevuto.

Manager e Validatore devono poter consultare le evidenze. Quando previsto, un Task successivo deve ricevere il materiale prodotto nelle fasi precedenti.

Evoluzione prevista dei Template: definizione per Task di documenti richiesti, obbligatori o facoltativi, categoria/tipo, produttore atteso, destinatari interni e regole di blocco.

## 8. Vista Validatore

Deve mostrare dati essenziali della pratica, avanzamento complessivo, Task completati, autore di ciascun Task, outcome, note ed evidenze prodotte, anomalie, area per outcome/nota/evidenze della validazione e comando Valida pratica. Non deve mostrare azioni manageriali di chiusura.

## 9. Scheda Pratica Manager

Deve mostrare riepilogo pratica, timeline e milestone rispetto alla scadenza finale X, avanzamento reale rispetto allo stato atteso, Task con assegnatario/stato/autore/priorità/scadenza operativa, note/risultati/evidenze, validatore e risultato validazione, risultato chiusura, fascicolo e audit distinti, azioni manageriali coerenti.

## 10. Dashboard Portfolio Manager

La home del WMS deve essere una Dashboard delle pratiche, non la pagina di una singola pratica.

Deve mostrare in cima le pratiche che richiedono attenzione e permettere filtri/viste per stato. Informazioni minime: cliente, tipo pratica, scadenza finale X, stato, avanzamento, milestone attesa, stato reale, anticipo/ritardo operativo, priority score/urgenza, responsabile/manager, blocchi o attese esterne.

## 11. Schedule Policy relativa a X

Ogni Tipo di Pratica deve poter definire milestone relative alla scadenza finale X.

Esempio configurativo discusso:

- task N-1/N entro X-6;
- task N/N entro X-4;
- validazione entro X-3;
- chiusura entro X-2;
- scadenza esterna X.

Gli offset appartengono al Template/Tipo Pratica e non sono valori globali. Il WMS deve calcolare lo stato atteso alla data corrente e confrontarlo con lo stato reale.

## 12. Priority Engine

La priorità deve essere principalmente calcolata dinamicamente. Input minimi: tempo residuo alla scadenza X, milestone attesa, avanzamento reale, scostamento reale/atteso, Task bloccati/dipendenze, criticità del tipo pratica, stato IN_ATTESA_ESTERNA, eventuale override del Manager.

La priorità deve ordinare sia il Portfolio Manager sia la Work Queue Operatore.

## 13. Task Context

Quando l'Operatore apre un Task, il WMS deve comporre il contesto operativo necessario: titolo/obiettivo, istruzioni operative, cliente/pratica, scadenza operativa, priorità, dipendenze, dati contestuali, evidenze/documenti precedenti, documenti richiesti, area note/allegati/esito e completamento.

## 14. Marker contestuali

Le istruzioni devono poter contenere marker racchiusi fra `%%` risolti dal contesto.

Esempio:

`A completamento inviare una email a %%mail_amministrativa%% e a %%mail_titolare%% per conoscenza.`

Sorgenti previste: anagrafica cliente, dati pratica, assegnazioni/ruoli, risultati/evidenze precedenti, connector futuri verso gestionali.

Esempi: %%cliente_ragione_sociale%%, %%cliente_codice_fiscale%%, %%mail_amministrativa%%, %%mail_titolare%%, %%telefono_amministrazione%%, %%periodo_pratica%%, %%data_scadenza%%, %%responsabile_pratica%%.

Un marker necessario non risolvibile deve essere segnalato; il Template deve poter stabilire se l'assenza è bloccante.

## 15. Gestione email integrata

Il WMS dovrà poter preparare una mail contestualizzata con destinatari da marker/anagrafica, oggetto codificato e contestualizzato, corpo precompilato, allegati dal fascicolo, anteprima prima dell'invio, archiviazione della mail e audit.

Esempio operativo:

`Invia al cliente %%mail_amministrazione%% la mail con allegato %%documento_F24%%.`

Principio operativo generale del progetto: una email non viene inviata senza che il contenuto sia stato prima mostrato e approvato dall'utente.

## 16. Correlazione email in ingresso

Le mail generate dal WMS devono poter essere correlate a Pratica e Task tramite codice leggibile nell'oggetto, header applicativi, Message-ID, In-Reply-To e References.

Il motore futuro deve poter identificare pratica/task, archiviare messaggio e allegati, produrre audit e, quando previsto, avanzare/sbloccare il workflow.

## 17. Task automatici ed event-driven

Non tutti i Task richiederanno completamento manuale. Eventi possibili: risposta email cliente, ricezione documento, esito da gestionale, firma completata, pagamento rilevato, raggiungimento di una data.

Stato previsto: IN_ATTESA_ESTERNA con reason code CLIENTE, ENTE, GESTIONALE, DOCUMENTO, FIRMA, PAGAMENTO.

Ogni avanzamento automatico deve essere auditabile e spiegabile.

## 18. Linguaggio e principi UI

Interfaccia professionale e sobria. Priorità a leggibilità, densità informativa e chiarezza. Desktop-first con responsive ragionevole. Stati, priorità e ritardi devono essere distinguibili senza dipendere esclusivamente dal colore. Un'azione non consentita non deve apparire disponibile.

Navigazione minima coerente:

Dashboard Manager -> Scheda Pratica -> dettagli Task

Work Queue Operatore -> Scheda Task -> ritorno automatico alla Work Queue dopo completamento

Dashboard/Scheda Pratica -> Vista Validatore quando pertinente

## 19. Dati demo per il prototipo UI

Per valutare realmente Dashboard e code operative servono almeno 12 pratiche, 6 clienti, 2 operatori, 1 validatore, 1 manager, tipi pratica differenti e casi in anticipo, in linea, in ritardo operativo e in attesa esterna simulata.

## 20. Criterio di accettazione UX

Aprendo il WMS senza spiegazioni, deve essere comprensibile cosa deve fare ciascun Operatore, quali pratiche richiedono attenzione e perché, cosa deve controllare il Validatore, cosa governa il Manager, la differenza fra stato reale e stato atteso e quali evidenze hanno prodotto le fasi precedenti.

## 21. Regola di sviluppo del progetto

Una issue alla volta.

Specifica -> implementazione Codex -> test/collaudo -> accettazione -> issue successiva.

Non cambiare baseline, branch o requisiti mentre Codex sta implementando una issue. Le issue successive restano parcheggiate fino all'accettazione della precedente.

Le PR sperimentali non devono essere considerate automaticamente baseline di prodotto: la baseline viene promossa solo dopo collaudo e accettazione.

## 22. Stato alla fine della sessione del 25 agosto 2026

La PR #7 è un esperimento v0.3 ricostruito da Codex partendo da una baseline non corretta. Contiene idee/codice potenzialmente recuperabili ma non è accettata e non deve essere mergeata automaticamente.

La issue #5 contiene la specifica UI-first delle cinque superfici operative ed è materiale fondamentale per la successiva implementazione, ma deve essere affrontata soltanto dopo avere ricostruito/accettato una baseline coerente comprendente i requisiti delle issue precedenti.

Questo documento, insieme alle issue #1-#5 e alla specifica evolutiva v0.3-v0.6, deve essere usato per evitare la perdita delle decisioni funzionali maturate.
