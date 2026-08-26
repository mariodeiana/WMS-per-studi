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

La pratica `NON_VALIDATA` viene evidenziata nella coda Manager (`MGR-LST`). Aprendo la pratica (`MGR-PRT`), il Manager deve trovare in evidenza la NC aperta, con almeno:

- codice NC;
- stato della NC;
- motivazione originaria;
- autore della rilevazione;
- data e ora;
- eventuali evidenze allegate alla validazione.

Il Manager prende in carico la NC e definisce la sanatoria. La responsabilità del Manager è quindi decidere come rientrare nel flusso operativo, senza modificare l'esito espresso dal Validatore.

### 3. Definizione dell'azione correttiva

Il Manager individua uno o più task da rieseguire e descrive l'azione correttiva. Esempio:

> Rieseguire l'elaborazione dopo verifica dei registri IVA e ripetere il controllo.

Può quindi selezionare, ad esempio:

- `LIPE-03 – Elaborazione dati LIPE`;
- `LIPE-04 – Controllo risultato elaborazione`.

L'avvio della sanatoria deve:

- collegare l'azione correttiva alla NC;
- riaprire i task selezionati, conservando come storico i risultati e gli allegati precedenti;
- consentire al Manager di confermare o modificare l'assegnatario dei task;
- portare la pratica nello stato `IN_LAVORAZIONE`;
- registrare nell'audit la motivazione della riapertura e il riferimento alla NC.

I task non interessati dalla NC restano completati e non vengono modificati.

### 4. Implementazione dell'azione correttiva

I task riaperti ricompaiono nella coda dell'Operatore (`OPR-LST`) secondo le normali regole di priorità e assegnazione.

Aprendo il task (`OPR-TSK`), l'Operatore deve vedere chiaramente che il task è stato riaperto per una NC, ad esempio:

> **Riaperto per NC-0001**  
> Rieseguire l'elaborazione dopo verifica dei registri IVA e ripetere il controllo.

L'Operatore lavora il task normalmente: può registrare note intermedie, allegati, diario di lavorazione e risultato finale. Il nuovo risultato non sostituisce né cancella quello precedente: entrambi rimangono nel fascicolo, distinguendo risultato storico e risultato corrente.

Quando tutti i task correttivi sono nuovamente completati e la pratica soddisfa i requisiti previsti, la pratica ritorna nello stato `DA_VALIDARE`.

La NC, invece, non viene chiusa automaticamente: passa allo stato `DA_VERIFICARE`.

### 5. Verifica della sanatoria

La pratica torna nella coda di validazione (`VAL-LST`). Nel dettaglio (`VAL-PRT`) il Validatore deve vedere che si tratta di una nuova verifica collegata a `NC-0001` e poter ricostruire il prima e il dopo:

- motivo originario della NC;
- azione correttiva definita dal Manager;
- task riaperti;
- nuovi risultati;
- nuove note ed evidenze;
- risultati storici precedenti alla correzione.

Se la nuova validazione ha esito `VALIDATA`, la NC viene chiusa e la pratica passa a `VALIDATA`.

Se l'esito è `VALIDATA_CON_RILIEVI`, occorre distinguere se il rilievo residuo è non bloccante e quindi compatibile con la chiusura della NC, oppure se richiede ulteriore azione correttiva.

Se l'esito è nuovamente `NON_VALIDATA`, non viene creata automaticamente una nuova NC per lo stesso problema. La NC originaria resta aperta e viene registrato un nuovo ciclo di sanatoria, mantenendo la sequenza completa dei tentativi di correzione.

### 6. Principio di separazione dei ruoli

Il flusso mantiene una separazione precisa delle responsabilità:

**Operatore esegue → Validatore giudica → Manager governa l'eccezione.**

Il Validatore rileva e descrive la Non Conformità. Il Manager definisce la risposta organizzativa e operativa. L'Operatore implementa le azioni correttive. Il Validatore verifica infine che la sanatoria sia sufficiente.

### 7. Ciclo sintetico della NC

`NON_VALIDATA → NC APERTA → presa in carico Manager → azione correttiva → task riaperti → nuova lavorazione → NC DA_VERIFICARE → nuova validazione → NC CHIUSA`

La NC è quindi l'oggetto che descrive e storicizza il problema; i task riaperti costituiscono le azioni operative necessarie per correggerlo.
