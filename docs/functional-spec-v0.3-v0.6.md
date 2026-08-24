# Specifica funzionale evolutiva WMS v0.3-v0.6

## 1. Risultato di lavoro

Ogni azione significativa del workflow deve produrre un risultato strutturato. Il concetto è comune a task operativo, validazione e chiusura.

Campi minimi concettuali:
- actor
- actor_role
- timestamp
- outcome
- note
- attachments/evidence
- related_practice_id
- related_task_code opzionale

L'audit registra il fatto che l'azione è avvenuta. Il fascicolo/evidence store conserva il contenuto prodotto.

## 2. Evidenze e fascicolo pratica

Le evidenze appartengono alla Pratica e possono essere originate da un Task, dalla Validazione, dalla Chiusura o da eventi esterni. Devono essere consultabili da Manager e Validatore e, quando previsto, rese disponibili alle attività successive.

Una successiva evoluzione dei Task Template potrà definire documenti richiesti, obbligatori o facoltativi, tipo/categoria, produttore atteso, destinatari interni del documento e regole di blocco.

## 3. Istruzioni operative del Task

Chi progetta il Template di Pratica deve poter definire per ogni Task istruzioni operative chiare. L'operatore non deve basarsi sulla memoria personale della procedura.

Requisiti:
- sempre ben visibili nella pagina della singola attività;
- visibili prima dell'azione di completamento;
- supporto a testo multilinea;
- futura possibilità di checklist/passaggi;
- supporto a marker contestuali.

Esempio template:

`A completamento inviare una email a %%mail_amministrativa%% e a %%mail_titolare%% per conoscenza.`

## 4. Context/Marker Engine

I marker sono token racchiusi fra `%%` e vengono risolti in base al contesto della pratica.

Sorgenti previste:
- anagrafica cliente;
- dati della pratica;
- assegnazioni/ruoli;
- risultati ed evidenze precedenti;
- in futuro connector verso gestionali esterni.

Esempi:
- `%%cliente_ragione_sociale%%`
- `%%cliente_codice_fiscale%%`
- `%%mail_amministrativa%%`
- `%%mail_titolare%%`
- `%%telefono_amministrazione%%`
- `%%periodo_pratica%%`
- `%%data_scadenza%%`
- `%%responsabile_pratica%%`

Se un marker necessario non è risolvibile, il WMS deve segnalarlo esplicitamente. Il template deve poter indicare se l'assenza blocca il completamento.

## 5. Task Context

Quando un operatore apre una singola attività, il WMS deve comporre il contesto operativo minimo necessario:
- titolo e obiettivo del task;
- istruzioni operative risolte;
- cliente e pratica;
- scadenza operativa;
- eventuali dipendenze;
- documenti/evidenze provenienti dalle fasi precedenti;
- documenti richiesti per il task;
- area note e allegati;
- comando di completamento.

## 6. Portfolio Dashboard

La home del WMS deve essere una vista di portafoglio, non la singola pratica.

Deve mostrare prima le pratiche che richiedono attenzione, poi consentire viste/filtri per stato. Informazioni minime per riga/card:
- cliente;
- tipo pratica;
- scadenza finale;
- stato;
- avanzamento;
- milestone attesa alla data odierna;
- ritardo/anticipo operativo;
- priority score;
- responsabile/manager;
- eventuali blocchi o attese esterne.

## 7. Schedule Policy relativa a X

Ogni Tipo di Pratica deve poter definire milestone relative alla data di scadenza finale X.

Esempio puramente configurativo:
- task N-1/N entro X-6;
- task N/N entro X-4;
- validazione entro X-3;
- chiusura entro X-2;
- scadenza esterna X.

Gli offset non sono globali: appartengono al template/tipo pratica.

Il WMS deve calcolare lo stato atteso alla data corrente e confrontarlo con lo stato reale.

## 8. Priority Engine

La priorità è principalmente un valore calcolato dinamicamente, non un semplice campo Alto/Medio/Basso.

Input minimi:
- tempo alla scadenza X;
- milestone corrente/attesa;
- avanzamento reale;
- scostamento rispetto allo stato atteso;
- task bloccati/dipendenze;
- criticità del tipo pratica;
- stato IN_ATTESA_ESTERNA;
- eventuale override/priorità manuale del Manager.

La priorità deve ordinare sia le pratiche nella Dashboard Manager sia le attività nella Work Queue Operatore.

## 9. Mail integrata

Il WMS dovrà poter preparare e successivamente inviare mail contestualizzate senza dipendere necessariamente dal client di posta locale.

Concetti:
- template destinatari;
- template oggetto;
- template corpo;
- marker contestuali;
- allegati provenienti dal fascicolo;
- anteprima/conferma prima dell'invio nelle prime versioni;
- archiviazione della mail inviata nel fascicolo e nell'audit.

Esempio operativo:

`Invia al cliente %%mail_amministrazione%% la mail con allegato %%documento_F24%%.`

## 10. Correlazione delle email ricevute

Una mail generata dal WMS dovrebbe contenere metadati correlabili a Pratica + Task.

Meccanismi previsti:
- codice leggibile nell'oggetto come fallback, ad es. `[WMS:P-2026-LIPE-001:TASK-LIPE-05]`;
- header applicativi dedicati quando possibile;
- Message-ID salvato;
- uso di In-Reply-To e References per le risposte.

Il motore di correlazione deve poter:
- identificare la pratica/task;
- archiviare messaggio e allegati;
- produrre eventi audit;
- aggiornare uno stato di attesa o sbloccare una fase successiva quando la regola lo prevede.

## 11. Task automatici ed event-driven

Non tutti i task richiedono azione manuale di completamento. Alcuni possono avanzare quando si verifica un evento.

Esempi:
- risposta email cliente;
- ricezione documento;
- esito da gestionale;
- firma completata;
- pagamento rilevato;
- raggiungimento di una data/termine.

Stato previsto: `IN_ATTESA_ESTERNA`, con reason code configurabile, ad esempio CLIENTE, ENTE, GESTIONALE, DOCUMENTO, FIRMA, PAGAMENTO.

Ogni avanzamento automatico deve essere tracciato e spiegabile tramite audit.

## 12. Principio di design

Il metodo operativo deve appartenere al WMS e ai suoi template, non alla memoria delle persone e non a uno specifico gestionale. Il sistema deve ridurre il lavoro necessario per eseguire correttamente una pratica, preservando tracciabilità, separazione dei ruoli e possibilità di integrazione con sistemi esterni.
