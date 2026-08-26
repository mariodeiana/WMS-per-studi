# Manuale operativo

## Rilevazione di una Non Conformità, definizione di una azione correttiva e sua implementazione

Una Non Conformità (NC) rappresenta un problema rilevato durante il controllo di una pratica che impedisce di considerarla validata nello stato corrente. La NC descrive il problema; le attività riaperte o assegnate descrivono invece le azioni correttive necessarie per sanarlo.

### 1. Rilevazione della Non Conformità

Il caso tipico nasce in fase di validazione. Il Validatore apre il dettaglio della pratica (`VAL-PRT`), esamina risultati, note ed evidenze e seleziona l'esito `NON_VALIDATA`.

La motivazione è obbligatoria. Esempio:

> Il totale IVA del periodo non coincide con il riepilogo contabile.

Alla registrazione dell'esito il sistema deve:

- registrare l'esito di validazione e la relativa motivazione;
- portare la pratica nello stato `NON_VALIDATA`;
- creare una NC collegata alla pratica, ad esempio `NC-0001`, nello stato `APERTA`;
- memorizzare origine, pratica interessata, Validatore, data/ora e descrizione della NC;
- mantenere inalterati risultati, allegati e audit già acquisiti.

La mancata validazione non riapre automaticamente alcun task. Il Validatore giudica la pratica ma non decide come correggerla.

### 2. Presa in carico da parte del Manager

La pratica `NON_VALIDATA` viene evidenziata nella coda Manager (`MGR-LST`). Aprendo la pratica (`MGR-PRT`), il Manager deve trovare in evidenza la NC aperta, con almeno codice NC, stato, motivazione originaria, autore della rilevazione, data/ora ed eventuali evidenze della validazione.

Il Manager prende in carico la NC e definisce la sanatoria. La responsabilità del Manager è decidere come rientrare nel flusso operativo, senza modificare l'esito espresso dal Validatore.

### 3. Definizione dell'azione correttiva

Il Manager individua uno o più task da rieseguire e descrive l'azione correttiva. Esempio:

> Rieseguire l'elaborazione dopo verifica dei registri IVA e ripetere il controllo.

L'avvio della sanatoria collega l'azione correttiva alla NC, riapre solo i task selezionati conservando risultati e allegati precedenti, permette di governarne l'assegnazione, porta la pratica in `IN_LAVORAZIONE` e registra nell'audit motivazione e riferimento alla NC. I task non interessati restano completati.

### 4. Implementazione dell'azione correttiva

I task riaperti ricompaiono nella coda dell'Operatore (`OPR-LST`) secondo le normali regole di priorità e assegnazione. In `OPR-TSK` l'Operatore vede chiaramente il riferimento alla NC e le istruzioni correttive.

L'Operatore lavora normalmente con note intermedie, allegati, diario e risultato finale. Il nuovo risultato non cancella quello precedente: entrambi restano nel fascicolo.

Quando tutti i task correttivi sono nuovamente completati, la pratica ritorna `DA_VALIDARE`; la NC passa a `DA_VERIFICARE` e non viene chiusa automaticamente.

### 5. Verifica della sanatoria

La pratica torna in `VAL-LST`. In `VAL-PRT` il Validatore deve poter ricostruire motivo originario, azione correttiva, task riaperti, nuovi risultati/evidenze e risultati storici.

`VALIDATA` chiude la NC e porta la pratica a `VALIDATA`. `VALIDATA_CON_RILIEVI` può chiudere la NC se il rilievo residuo è non bloccante. Una nuova `NON_VALIDATA` non crea automaticamente una seconda NC per lo stesso problema: la NC originaria viene riaperta e registra un nuovo ciclo di sanatoria.

### 6. Principio di separazione dei ruoli

**Operatore esegue → Validatore giudica → Manager governa l'eccezione.**

Il Validatore rileva e descrive la Non Conformità. Il Manager definisce la risposta organizzativa e operativa. L'Operatore implementa le azioni correttive. Il Validatore verifica infine la sanatoria.

### 7. Ciclo sintetico della NC

`NON_VALIDATA → NC APERTA → presa in carico Manager → azione correttiva → task riaperti → nuova lavorazione → NC DA_VERIFICARE → nuova validazione → NC CHIUSA`

La NC è l'oggetto che descrive e storicizza il problema; i task riaperti costituiscono le azioni operative necessarie per correggerlo.

### 8. Registro operativo NC / Azioni Correttive

Le NC non devono essere consultabili esclusivamente entrando nelle singole pratiche. Il Manager deve disporre di un registro trasversale dedicato, identificato come `MGR-NCL` — Non Conformità e Azioni Correttive.

Il registro presenta una riga per NC e deve consentire di controllare almeno: codice NC, cliente, pratica, data di apertura, origine, descrizione sintetica, stato NC, azione correttiva definita, task coinvolti, stato di attuazione dell'azione correttiva e data dell'ultima evoluzione.

Gli stati della NC sono inizialmente: `APERTA`, `IN_SANATORIA`, `DA_VERIFICARE`, `CHIUSA`.

Lo stato dell'Azione Correttiva viene derivato dallo stato dei task collegati, evitando duplicazioni informative: `DA_ATTUARE → IN_CORSO → ATTUATA → VERIFICATA`.

La selezione di una NC da `MGR-NCL` porta inizialmente alla relativa `MGR-PRT`, posizionata sul contesto della Non Conformità. Un dettaglio NC autonomo (`MGR-NCD`) sarà introdotto solo se l'evoluzione funzionale lo renderà necessario.

Gli stessi dati alimenteranno la futura dashboard Manager (`MGR-DSH`), che dovrà sintetizzare almeno NC aperte, in sanatoria, da verificare e ferme/scadute.

## Interfacce applicative consolidate

- `MGR-LST` — coda/lista delle pratiche in esecuzione del Manager;
- `MGR-PRT` — dettaglio della pratica per il Manager;
- `MGR-TSK` — dettaglio del task per il Manager;
- `MGR-NCL` — registro Non Conformità e Azioni Correttive;
- `MGR-DSH` — dashboard generale Manager, prevista;
- `OPR-LST` — coda dei task dell'Operatore;
- `OPR-TSK` — dettaglio operativo del task;
- `VAL-LST` — coda delle pratiche da validare, con validazioni recenti;
- `VAL-PRT` — dettaglio e decisione di validazione.

In modalità runtime `debug` il codice dell'interfaccia viene mostrato nella testata fissa.
