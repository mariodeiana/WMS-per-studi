> Manuale 1.4.1, precedente al Repertorio SQL. IP corretto il 22 settembre 2026. Novità: [stato e decisioni](../stato-e-decisioni.md).

# WMS per studi — Manuale operativo
## Versione e ambito
Versione applicativa documentata: 1.4.1 del 20.09.26. Edizione del manuale: 21 settembre 2026.
Ambiente di riferimento: TEST, http://192.168.11.10:8001.
Destinatari: operatori, supervisori, validatori e amministratori dello studio.

Questo manuale descrive le interfacce e le regole presenti nella versione indicata. La redazione è basata sui modelli delle schermate e sul comportamento applicativo verificato nel codice TEST; le viste supervisore, storico e documenti clienti sono state anche controllate nel browser durante il rilascio. Non costituisce una certificazione delle scadenze fiscali. Le date dei casi di esempio sono dati operativi di TEST.

Le tabelle spiegano i campi nell'ordine di utilizzo: che cosa rappresentano, chi li compila e quale effetto producono. “Consultazione” significa che il campo viene mostrato dal sistema; “compilazione” indica un dato inseribile dall'utente. I pulsanti possono apparire solo quando ruolo e stato consentono l'azione.

## 1. Concetti fondamentali
| Termine | Significato operativo |
|---|---|
| Cliente | Soggetto al quale sono associate le pratiche. Il codice cliente lo identifica e consente di raccogliere i documenti delle diverse pratiche. |
| Tipo di pratica o modello | Schema riutilizzabile: attività, gruppi responsabili, esiti, collegamenti e regole di scadenza. Esempi: Bilanci, Dichiarazione IVA, IMU. |
| Pratica cliente | Una singola esecuzione di un modello per un cliente e un periodo. Ha un proprio codice, una scadenza, attività, note, risultati e documenti. |
| Attività o task | Un lavoro concreto da eseguire all'interno della pratica. L'interfaccia usa entrambi i termini. |
| Gruppo responsabile | Gruppo di operatori al quale è assegnata l'attività. Non coincide con l'operatore che la prende in carico. |
| Appartenenza | Collegamento fra un utente e un gruppo. Il gruppo determina il ruolo esercitato in quel contesto. |
| Esito | Risultato scelto al completamento. Può determinare quali attività si attivano successivamente. |
| Transizione | Collegamento da un'attività a una o più attività successive, associato a un esito. |
| Nodo iniziale | Attività che si attiva quando nasce la pratica. Più nodi iniziali avviano più rami. |
| Fine ramo | Termine di un percorso del grafo. Non equivale alla chiusura amministrativa dell'intera pratica. |
| Evidenza | Documento allegato durante lavorazione, completamento, validazione o chiusura. |
| Fascicolo | Insieme consultabile di attività, note, risultati, documenti ed eventi della pratica. |
| Audit | Cronologia delle operazioni registrate dal sistema, con autore, data e dettagli. |
| Bozza del modello | Disegno salvato per riprendere la progettazione. Non sostituisce il modello pubblicato finché non si preme Salva modifiche. |

### 1.1 Ruoli
| Ruolo | Compiti e interfacce |
|---|---|
| Operatore | Lavora le attività del gruppo attivo; salva note e documenti; registra gli esiti. Usa I miei compiti e il dettaglio attività. |
| Supervisore | Controlla tutte le pratiche della lista disponibile; assegna attività ai gruppi; riapre attività; gestisce sanatorie; chiude pratiche; consulta storico e documenti clienti. Nell'applicazione è identificato anche come MANAGER. |
| Validatore | Esamina le pratiche che richiedono validazione, registra l'esito e le eventuali motivazioni. Non può validare una pratica della quale abbia eseguito attività. |
| Amministratore | Gestisce utenti, gruppi, appartenenze, clienti, modelli e creazione delle pratiche. Può consultare il fascicolo; i comandi operativi dipendono comunque dal ruolo attivo. |
| Decisore | Ruolo presente nel catalogo, ma senza una scrivania specifica nella versione 1.4.1. Il contesto invita a selezionare un ruolo operativo disponibile. |

Un utente può avere più appartenenze. Cambiare ruolo non crea un altro utente: cambia la scrivania e le azioni disponibili. Per lavorare come operatore occorre selezionare anche il corretto gruppo tramite la relativa appartenenza.

### 1.2 Ciclo di una pratica
Senza validazione: Da fare → In corso → Completata → Chiusa.
Con validazione: Da fare → In corso → Da validare → Validata → Chiusa.
Se la validazione è negativa: Non validata → azione correttiva del supervisore → In corso → nuova validazione.

“Completata” significa che tutte le attività raggiunte dal percorso sono state eseguite. “Chiusa” significa che il supervisore ha registrato la chiusura finale. Una pratica completata può quindi restare nella scrivania supervisore.

## 2. Accesso, testata e navigazione
### 2.1 Schermata Accesso
| Campo o comando | Uso |
|---|---|
| Utente | Inserire il login assegnato. Gli spazi esterni vengono rimossi. Non è necessariamente uguale al nome visualizzato. |
| Password | Inserire la password personale; i caratteri sono nascosti. Il manuale non contiene credenziali. |
| Accedi | Invia le credenziali. Durante la richiesta compare Accesso… e il pulsante non è disponibile. |
| Messaggio di errore | Segnala credenziali o accesso non validi oppure problemi di connessione. Correggere il dato o riprovare secondo il messaggio. |

Dopo l'accesso si apre la scrivania del contesto attivo. In caso di sessione scaduta l'applicazione può tornare alla schermata di accesso.

### 2.2 Testata comune
| Elemento | Significato e azione |
|---|---|
| Logo e WMS | Collegamento alla pagina iniziale del ruolo attivo. |
| Indicatore TEST | Identifica l'ambiente di lavoro. Controllarlo prima di operare. |
| Workflow Management System Rel. X.y.z del gg.mm.aa | Versione del programma e data della release; non è la data corrente né il periodo della pratica. |
| Nome utente | Persona autenticata. |
| Ruolo attivo | Menu delle appartenenze disponibili. Selezionare, ad esempio, Supervisore o Operatore · Contabili. Il cambio porta alla relativa scrivania. |
| Esci | Chiude la sessione e torna all'accesso. |
| Collegamento Scrivania | Riporta alla pagina principale del contesto. |
| Percorso di navigazione | Collegamenti sopra il fascicolo o dettaglio attività per risalire alla lista o alla pratica. |

Le linguette selezionate sono evidenziate. Nelle serie di linguette è disponibile la navigazione con frecce destra/sinistra, Home ed End. Il tabulatore consente di raggiungere campi e comandi.
I messaggi Caricamento e Salvataggio indicano richieste in corso. Un pulsante disabilitato può indicare un'operazione in corso, un campo obbligatorio mancante o uno stato che non permette l'azione.

## 3. Scrivania operatore — I miei compiti
La lista riguarda il gruppo dell'appartenenza attiva. Le attività future non ancora raggiunte dal percorso non sono proposte come lavoro da svolgere.

### 3.1 Testata e quadranti
| Elemento | Spiegazione |
|---|---|
| I miei compiti | Titolo della scrivania. Comprende lavoro disponibile nel gruppo e già preso in carico dall'utente. |
| Aggiorna | Rilegge la situazione dal server, utile dopo interventi di colleghi o supervisore. |
| Da lavorare | Numero delle attività disponibili per l'utente nella relativa linguetta. Il denominatore indicato sotto comprende anche quelle in carico ai colleghi. |
| Scadute | Attività da lavorare con data precedente a oggi. |
| In corso | Attività nella lista Da lavorare già avviate. |
| Riaperte | Attività tornate lavorabili dopo una riapertura del supervisore. |
| Anello del quadrante | Rappresentazione della quota rispetto al totale indicato; non è una misura delle ore lavorate. |

### 3.2 Linguette e filtri
| Elemento | Uso |
|---|---|
| Da lavorare | Attività eseguibili non riservate a un altro operatore: libere oppure già in carico all'utente. |
| In carico ai colleghi | Attività dello stesso gruppo riservate ad altri operatori. |
| Completate · ultime 8 ore | Completamenti dell'utente nelle ultime otto ore, nell'ambito del gruppo attivo. Non è lo storico integrale. |
| Numero sulla linguetta | Totale della sezione prima dei filtri di ricerca. |
| Cerca attività | Cerca testo in attività, cliente, pratica, operatore e note disponibili. La ricerca non distingue maiuscole e minuscole. |
| Mostra | Nella linguetta Da lavorare: Tutte le attività, Scadute e attive, In corso, Riaperte. |
| X di Y attività | Numero dei risultati filtrati rispetto alle attività della sezione. |
| Azzera filtri | Quando proposto nella lista vuota, cancella testo e filtro Mostra. |

### 3.3 Colonne
| Colonna | Contenuto |
|---|---|
| Cliente | Codice e denominazione del cliente. |
| Pratica | Tipo e identificativo della pratica di provenienza. |
| Attività | Codice e titolo; il titolo può aprire il dettaglio. Espone eventuali note e motivo di riapertura tramite sezioni apribili. |
| Scadenza | Data dell'attività; se assente, data della pratica. |
| Completata il | Nella sezione recente sostituisce Scadenza e mostra data e ora della registrazione del risultato. |
| Stato | Da fare, In corso, Riaperta o Occupata secondo la situazione operativa. |
| Esito | Nella sezione completate mostra il risultato registrato. |
| Priorità | Presente in Da lavorare: livello e distanza dalla scadenza. |
| Apri | Apre un'attività disponibile. La semplice apertura non costituisce ancora presa in carico. |
| Riprendi | Rientra in una lavorazione già avviata. |
| Consulta | Apre un'attività consultabile, ad esempio un completamento recente. |
| Non disponibile | L'attività è riservata a un collega; non è un errore di caricamento. |

### 3.4 Lucchetto e colori
Il lucchetto indica una presa in carico esclusiva dell'attività. Non significa che il collega sia online e non blocca tutte le altre attività della pratica. La presa in carico si registra quando l'operatore salva il lavoro o completa l'attività. Se due persone hanno aperto lo stesso lavoro libero, il controllo sul server impedisce al secondo di salvarlo dopo la presa in carico da parte del primo.

Il bordino sinistro è di 8 pixel. Nella lista operatore è rosso per attività scadute nella sezione Da lavorare, arancione per attività riaperte nella stessa sezione, verde negli altri casi. Il rosso ha precedenza. Una riga verde in Completate o In carico ai colleghi non certifica l'assenza di rilievi: leggere sempre stato ed esito.

### 3.5 Priorità temporale
| Livello | Condizione |
|---|---|
| In ritardo | Scadenza precedente a oggi. |
| Alta | Scadenza fra oggi e i prossimi 7 giorni, compresi. |
| Media | Scadenza fra 8 e 30 giorni. |
| Bassa | Scadenza oltre 30 giorni. |

La priorità è calcolata dalla data; non è un campo liberamente impostabile. “Oggi”, “Domani”, “Tra … gg” e “Scaduta da … gg” descrivono la distanza temporale. Le date configurate non sono aggiornate da un calendario fiscale automatico.

## 4. Dettaglio attività dell'operatore
### 4.1 Riepilogo
| Campo | Spiegazione |
|---|---|
| Tipo pratica e codice attività | Identificano il contesto del lavoro. |
| Titolo | Descrive l'attività da eseguire. |
| Stato | Da fare, In corso, Completata o In attesa. |
| Cliente | Codice cliente della pratica. |
| Periodo | Intervallo di riferimento della pratica, distinto dalla scadenza. |
| Scadenza attività | Termine operativo specifico oppure scadenza della pratica in assenza di un termine specifico. |
| Dipendenze | Eventuali prerequisiti espliciti conservati nel modello. Non confonderli con le transizioni del grafo. |
| Riaperta dal Supervisore | Motivazione da leggere prima di riprendere la lavorazione. |
| Istruzioni operative | Indicazioni definite nel modello; se assenti, compare Nessuna istruzione definita. |

### 4.2 Pannello Lavorazione
| Campo o comando | Obbligatorietà ed effetto |
|---|---|
| Indicazione di presa in carico | Mostra il titolare oppure Disponibile per la presa in carico. |
| Nota di lavoro | Testo libero sulle operazioni svolte. Con un salvataggio intermedio crea una nuova annotazione non vuota nel diario. Con il completamento diventa la nota del risultato. |
| Evidenze | Allegati da salvare insieme al lavoro o all'esito. Vedere il capitolo Documenti. |
| Esito | Obbligatorio per completare, non per salvare una lavorazione intermedia. Le opzioni dipendono dal modello; in assenza di opzioni configurate sono proposti Positivo e Con rilievi. |
| Salva e torna ai compiti | Salva nota e allegati, prende in carico l'attività se libera, la porta In corso e torna alla lista. Non attiva il passo successivo. |
| Registra risultato e completa | Richiede un esito. Salva il risultato, completa l'attività e attiva le destinazioni previste da quell'esito; torna alla lista. |

Il campo della nota non viene usato come editor per sovrascrivere tutte le annotazioni precedenti: le note salvate restano nel diario. All'apertura la casella di inserimento può essere vuota anche se esistono note storiche.
Il pannello di lavorazione non è mostrato per attività completate o non attive. Per correggere un'attività completata serve una riapertura consentita al supervisore.

### 4.3 Fascicolo attività
| Linguetta | Contenuto |
|---|---|
| Risultati attività | Esiti della specifica attività, con nota, autore, data e documenti associati. |
| Diario | Annotazioni salvate durante il lavoro e motivazioni di riapertura; gli allegati di lavorazione sono consultabili nella relativa sezione. |
| Attività precedenti | Contesto costituito dagli altri risultati già registrati nella pratica, anche di rami diversi. Il nome non implica che tutti siano predecessori diretti nel grafo. |
| Documenti | Allegati collegati alla specifica attività. |

Il numero sulla linguetta conta gli elementi della sezione. L'autore import-excel, quando presente nei dati caricati, identifica la registrazione di importazione e non attribuisce il lavoro originale a una persona dello studio.

### 4.4 Procedura operativa consigliata
1. Selezionare l'appartenenza del gruppo corretto.
2. Aprire Da lavorare e leggere cliente, pratica e scadenza.
3. Aprire l'attività, leggere istruzioni ed eventuale motivo della riapertura.
4. Consultare risultati e documenti di contesto.
5. Scrivere una nota concreta e allegare gli eventuali documenti.
6. Se il lavoro non è finito, usare Salva e torna ai compiti.
7. Se è finito, scegliere l'esito corretto e usare Registra risultato e completa.
8. Verificare nella scrivania il completamento e l'eventuale attività successiva.

## 5. Scrivania supervisore — Pratiche attive
### 5.1 Testata e quadranti
| Elemento | Significato |
|---|---|
| Pratiche in esecuzione | Elenco delle pratiche non formalmente chiuse. Include quelle completate o validate che attendono la chiusura. |
| Avanzamento | Percentuale complessiva calcolata sulle attività raggiunte delle pratiche caricate nella vista, non media semplice delle percentuali delle righe. |
| Critiche | Pratiche scadute oppure Non validate; una pratica che soddisfa entrambe le condizioni viene contata una volta. |
| Con rilievi | Pratiche classificate dalla lista come aventi risultati di attività con rilievi. |
| In scadenza | Pratiche con scadenza da oggi ai prossimi 7 giorni. |

I quadranti sono riferiti all'insieme della vista attiva e non ai soli risultati ridotti dai filtri di colonna. Nelle viste Storico e Documenti clienti non vengono mostrati come indicatori dell'archivio; la testata mantiene l'allineamento.

### 5.2 Colonne, filtri e comandi
| Elemento | Uso e interpretazione |
|---|---|
| Cliente | Codice e nome. Il campo Nome o codice… restringe la lista per corrispondenza testuale. |
| Pratica | Codice del tipo e identificativo della singola pratica. Il menu filtra per tipo; il collegamento apre il fascicolo. |
| Periodo | Inizio e fine dell'esercizio o intervallo di riferimento. |
| Scadenza | Termine della pratica, distinto dalle scadenze eventualmente anticipate delle singole attività. |
| Stato | Stato complessivo del flusso. |
| Avanzamento | Attività completate su attività raggiunte, percentuale e codici delle attività attualmente eseguibili. |
| Situazione | Regolare, Con rilievi o Non validata secondo la classificazione della lista. Il menu filtra queste categorie. |
| Priorità | Livello calcolato rispetto alla scadenza della pratica. |
| X di Y pratiche | Risultati dopo i filtri rispetto alle pratiche della vista. |
| Azzera filtri | Rimuove i filtri della lista. È disabilitato quando non ce ne sono. |

Il denominatore dell'avanzamento cresce quando il percorso raggiunge altre attività. Per esempio, un primo nodo completato che attiva il secondo può produrre 1/2, anche se il modello contiene ulteriori fasi future. Nei percorsi alternativi le attività mai raggiunte non devono essere interpretate come lavoro arretrato.

### 5.3 Bordini della lista supervisore
| Colore | Regola effettiva |
|---|---|
| Verde | Riga senza le condizioni rosse o arancioni della lista. |
| Arancione | Situazione classificata Con rilievi. |
| Rosso | Pratica scaduta oppure Non validata. Prevale sull'arancione. |

La larghezza è 8 pixel. Regolare è una classificazione operativa della lista, non una certificazione fiscale, contabile o documentale. Una riapertura non va dedotta soltanto dal colore della riga pratica: consultare il fascicolo. Nello storico una pratica chiusa è indicata come Conclusa e non come scaduta soltanto perché la sua vecchia scadenza è trascorsa.

## 6. Supervisore — Storico
La linguetta Storico comprende tutte le pratiche disponibili, comprese quelle ancora aperte. Per cercare soltanto le chiuse usare Stato = Chiusa quando tale stato è presente nei dati.

| Campo o comando | Spiegazione |
|---|---|
| Esercizio | Filtra per anno della data di inizio del periodo. Un periodo a cavallo d'anno è classificato secondo l'anno iniziale. |
| Stato | Filtra uno degli stati presenti nell'insieme caricato. Un'opzione non compare se non esistono pratiche di quello stato. |
| Cliente | Ricerca per nome o codice, combinabile con gli altri filtri. |
| Pratica | Filtro per tipo di pratica. |
| Situazione | Filtro della classificazione operativa della lista. |
| Chiusa il | Data di registrazione della chiusura, quando disponibile. Non è la scadenza. |
| Ordinamento | Chiusure più recenti prima; le pratiche aperte seguono per fine periodo decrescente. |
| Collegamento della pratica | Apre lo stesso fascicolo completo consultabile dalla vista attiva. |
| Azzera filtri | Rimuove anche esercizio e stato. |

Passare fra Pratiche attive e Storico azzera i filtri della lista. Il ritorno al supervisore da un fascicolo apre la scrivania: la versione attuale non offre un collegamento che ricostruisca automaticamente l'ultima ricerca storica.

Per cercare, ad esempio, un bilancio completato: aprire Storico, selezionare l'esercizio, scegliere BILANCI e Completata, poi inserire nome o codice del cliente. “Completata” e “Chiusa” sono filtri diversi.

## 7. Supervisore — Documenti clienti
La linguetta raccoglie i documenti effettivamente allegati a tutte le pratiche del cliente, aperte e chiuse. Non crea copie dei file e non genera automaticamente i documenti nominati nelle note.

### 7.1 Scelta del cliente
| Campo | Uso |
|---|---|
| Cerca cliente | Filtra l'elenco dei clienti per nome o codice, senza distinguere maiuscole e minuscole. |
| Cliente | Selezione del cliente da consultare. Ogni voce mostra nome, codice e numero documenti. |
| Nome cliente | Titolo del catalogo selezionato. |
| Numero pratiche | Totale delle pratiche del cliente, anche se prive di allegati. |
| Documenti complessivi | Totale dei documenti del cliente prima dei filtri del catalogo. |

L'anagrafica comprende anche clienti senza documenti. Dopo aver cambiato cliente, la lista documenti e i relativi filtri vengono aggiornati. La ricerca cliente può mantenere visibile il cliente già selezionato, anche mentre si cerca un altro nome.

### 7.2 Filtri del catalogo
| Campo | Uso |
|---|---|
| Tipo documento | Seleziona una categoria presente negli allegati del cliente. Il valore predefinito per un allegato non classificato è DOCUMENTO. |
| Descrizione o nome file | Ricerca nel testo della descrizione e nel nome del file. |
| Pratica di provenienza | Seleziona la singola pratica identificata da tipo, anno iniziale del periodo e codice. Compaiono le pratiche con documenti nel catalogo. |
| Azzera filtri | Cancella tipo, testo e pratica di provenienza; mantiene il cliente selezionato. |
| X di Y documenti | Risultati dopo i filtri sul totale degli allegati del cliente. |

### 7.3 Colonne del catalogo
| Colonna | Contenuto e azioni |
|---|---|
| Tipo | Classificazione indicata al caricamento. È testo libero: F24 e Delega F24 possono diventare categorie distinte. Conviene adottare nomi uniformi nello studio. |
| Documento e descrizione | Nome originale del file e descrizione. Se mancante compare Descrizione non indicata. |
| Pratica di provenienza | Collegamento al fascicolo; mostra tipo, codice, periodo, indicazione Pratica aperta/chiusa ed eventuale attività di origine. |
| Data e autore | Data e ora della registrazione dell'allegato e utente autore. Non sono necessariamente la data del documento o dell'adempimento. |
| Apri | Apre l'anteprima in un'altra scheda; la visualizzazione dipende anche dal formato e dal browser. |
| Scarica | Scarica il file associato alla riga. |

Il catalogo è ordinato per tipo, descrizione e riferimenti di provenienza. Non unifica automaticamente due caricamenti distinti dello stesso contenuto: lo stesso file allegato a due pratiche rimane riconoscibile nelle due provenienze.
Nella versione attuale non ci sono caricamento diretto dall'archivio cliente, modifica della classificazione di un file già salvato, ricerca dentro il contenuto, OCR o esportazione massiva. I documenti si aggiungono nelle lavorazioni e nelle decisioni sulla pratica.

## 8. Fascicolo pratica — Riepilogo e consultazione
Il fascicolo è raggiungibile dalla lista supervisore, dallo storico, dalla coda del validatore, dall'amministrazione e dai collegamenti di provenienza dei documenti.

### 8.1 Testata e riepilogo
| Campo | Spiegazione |
|---|---|
| Tipo pratica | Titolo del fascicolo. |
| Identificativo | Codice univoco della singola pratica. |
| Stato | Stato complessivo corrente. |
| Cliente | Nome, se disponibile, e codice. |
| Periodo | Intervallo di riferimento. |
| Scadenza | Termine della pratica. |
| Percorso raggiunto | Completate/totale delle attività raggiunte e percentuale. |
| Fascicolo / Grafo | Due modi di consultare la stessa pratica. Il Grafo non è l'editor del modello. |

### 8.2 Dove siamo
Mostra la fase corrente e le attività non completate del percorso raggiunto. Per ciascuna: titolo, codice, operatore in carico o Da prendere in carico, gruppo, stato e scadenza. Il collegamento apre il dettaglio.
I contatori indicano attività aperte, documenti ed esiti registrati. Il pulsante dei documenti porta all'archivio del fascicolo.

### 8.3 Punti di attenzione e ultime annotazioni
Punti di attenzione elenca non conformità aperte, attività riaperte, esiti con rilievi e scadenze superate nelle pratiche operative. L'assenza di segnalazioni significa assenza di tali condizioni registrate.
Ultime annotazioni mostra un riepilogo recente con testo, codice attività, autore e data. Per la storia completa aprire l'attività: questo riquadro è solo un'anteprima.

### 8.4 Attività del fascicolo
| Elemento della riga | Spiegazione |
|---|---|
| Simbolo e stato | Completata, riaperta o altra condizione del task. |
| Codice e titolo | Identificano la fase. |
| Autore o assegnatario | Chi ha completato o preso in carico; in assenza, Da prendere in carico. |
| Gruppo | Responsabilità organizzativa della fase. |
| Data | Data del risultato per attività completate, altrimenti scadenza. |
| Esito | Risultato corrente, se presente. |
| Estratto della nota | Ultima annotazione o nota di esito disponibile. |
| Numero note e documenti | Quantità degli elementi associati all'attività. |
| Apri | Espande la riga senza uscire dalla pratica. |
| Apri dettaglio e gestione | Porta alla pagina della singola attività, con i comandi consentiti al ruolo. |

La riga espansa separa Annotazioni di lavoro, Esiti e relative note e Documenti dell'attività. I risultati precedenti non più correnti sono marcati Storico. Le attività non raggiunte si consultano nel Grafo.

### 8.5 Archivio completo
| Linguetta | Contenuto |
|---|---|
| Risultati | Esiti di attività, validazioni e chiusure, con note, autore, data e documenti collegati. |
| Tutti i documenti | Allegati con indicazione dell'attività di origine oppure Documento della pratica. |
| Audit | Eventi registrati dal sistema. Aprire una voce per vedere i dettagli. |

Nel dettaglio di una singola attività, le sezioni sono filtrate per quella attività. Per esaminare documenti e decisioni dell'intera pratica, tornare al fascicolo generale.
Ultimi eventi nella colonna laterale presenta una selezione della cronologia. Apri audit completo porta alla linguetta Audit.

## 9. Dettaglio e gestione attività del supervisore
| Campo o sezione | Funzione |
|---|---|
| Stato / Non raggiunta | Distingue lavoro completato, in corso o non attivato dal percorso. |
| Obbligatoria / Facoltativa | Indicazione del dato memorizzato. Nell'editor corrente ogni attività raggiunta deve essere completata per terminare il percorso. |
| Cosa deve essere fatto | Istruzioni operative. |
| Gruppo responsabile | Gruppo assegnato. |
| Scadenza attività | Termine del task. |
| In carico a | Utente che ha acquisito la lavorazione. |
| Completata da | Autore del completamento corrente. |
| Ultima nota di lavoro | Ultima nota corrente, se presente. Le annotazioni precedenti restano nel fascicolo. |
| Task riaperto | Motivazione della riapertura. |
| Percorso e dipendenze | Prerequisiti espliciti e destinazioni previste per esito. |
| Risultato corrente | Esito, nota, autore e data dell'ultimo risultato valido per il task. |

### 9.1 Assegnazione a un gruppo
Gruppo assegnatario è un menu. Scegliere un gruppo diverso e premere Assegna al gruppo. Il comando è mostrato per attività non completate di pratiche non validate e non chiuse.
La riassegnazione modifica il responsabile organizzativo e libera la precedente presa in carico personale. Non assegna direttamente il lavoro a uno specifico dipendente.

### 9.2 Riapertura
Motivo della riapertura è obbligatorio. Scrivere che cosa deve essere rivisto e premere Riapri task.
Si riapre un'attività completata prima della validazione finale/chiusura. Il lavoro torna disponibile secondo la responsabilità del gruppo; risultati ed evidenze precedenti restano consultabili.
Una correzione non può scegliere un esito che cambi le destinazioni del percorso già attraversato. La riapertura serve a correggere il lavoro, non a riscrivere liberamente la storia del grafo.

## 10. Non conformità e sanatoria
Una validazione Non validata apre, o riapre, una non conformità. Nel fascicolo si trovano identificativo, stato, motivazione, autore e data di apertura.

| Campo o comando | Uso |
|---|---|
| Attività da riaprire | Caselle delle attività completate interessate dalla correzione. Selezionarne almeno una. |
| Istruzioni per la correzione | Descrizione obbligatoria dell'intervento richiesto agli operatori. |
| Avvia sanatoria | Registra l'azione correttiva e riapre le attività selezionate. |
| Azioni correttive | Storico di istruzioni, attività coinvolte, autore, data di creazione e completamento. |
| Chiusa da / data | Dati della chiusura della non conformità dopo verifica positiva. |

Gli stati sono Aperta, In sanatoria, Da verificare e Chiusa. Il completamento delle correzioni porta a una nuova verifica; non sana automaticamente la non conformità senza l'esito del validatore.
Per una pratica Non validata utilizzare il percorso di sanatoria, così le attività corrette rimangono collegate alla non conformità.

## 11. Validatore — Scrivania e decisione
### 11.1 Pratiche da validare
| Colonna | Significato |
|---|---|
| Pratica / Cliente | Tipo e codice pratica cliccabili, con codice cliente. |
| Periodo | Riferimento temporale della pratica. |
| Scadenza | Termine e priorità temporale. |
| Attività | Completate sul totale raggiunto. |
| Situazione | Classificazione operativa della pratica. |
| Attesa | Ore trascorse dall'ingresso nello stato Da validare e relativa data/ora. |

Le mie validazioni nelle ultime 8 ore mostra le decisioni recenti dell'utente, con esito, momento e nota. È una vista temporanea personale, diversa dallo storico completo del supervisore.
Aprire il collegamento della pratica per esaminare fascicolo, documenti, risultati e grafo prima della decisione.

### 11.2 Pannello Validazione
| Campo o comando | Regola |
|---|---|
| Esito | Obbligatorio. Opzioni: Validata, Validata con rilievi, Non validata. |
| Motivazione / nota | Facoltativa per Validata; obbligatoria per Validata con rilievi e Non validata. |
| Evidenze | Documenti che supportano la decisione. |
| Registra validazione | Salva esito, nota e documenti. È disponibile quando la pratica è Da validare e i dati necessari sono completi. |

Validata e Validata con rilievi portano allo stato complessivo Validata. Il dettaglio del risultato conserva la distinzione fra i due esiti. Non validata porta allo stato Non validata e richiede la gestione della correzione.
La stessa persona che ha eseguito attività della pratica non può validarla, anche se dispone di entrambe le appartenenze. Cambiare ruolo non supera questo controllo.

## 12. Supervisore — Chiusura della pratica
La chiusura è disponibile nel fascicolo generale quando il percorso è completato e, se richiesta, la validazione è positiva. Non si chiude una pratica con non conformità ancora aperte.

| Campo o comando | Uso |
|---|---|
| Esito | Selezionare Chiusa oppure Chiusa con rilievi. È obbligatorio. |
| Nota di chiusura | Testo finale; l'interfaccia attuale non lo rende obbligatorio, ma è utile per descrivere eventuali rilievi. |
| Evidenze | Eventuali documenti della chiusura. |
| Registra risultato e chiudi | Registra la decisione e porta la pratica a Chiusa. |

Una pratica chiusa scompare dalla lista Pratiche attive e resta nello Storico. I suoi documenti continuano a comparire nell'archivio cliente.
Nella versione 1.4.1 non è presente un comando ordinario per riaprire una pratica già chiusa. Non confondere la riapertura di un task prima della validazione con la riapertura dell'intera pratica chiusa.

## 13. Documenti ed evidenze — Campi comuni
Il componente Evidenze ricorre nella lavorazione operatore, validazione e chiusura.

| Campo o comando | Spiegazione |
|---|---|
| + Aggiungi documenti | Seleziona uno o più file dal computer. Il caricamento effettivo avviene con il salvataggio o la registrazione dell'operazione principale. |
| Nome del file | Nome del file selezionato; usato per riconoscerlo nelle liste. |
| Descrizione | Testo libero, ad esempio “Delega acconto IMU — immobili cliente — esercizio 2026”. |
| Tipo documento | Testo libero; valore iniziale DOCUMENTO. Esempi organizzativi: F24, RICEVUTA, BILANCIO, VERBALE. Questi esempi non sono un catalogo obbligatorio del programma. |
| × / Rimuovi | Toglie il file dalla selezione non ancora salvata; non cancella un documento storico già registrato. |
| Limite dimensione | Massimo 5 MB per singolo documento. Un file troppo grande viene segnalato. |
| Apri anteprima / Apri | Apre il documento in un'altra scheda, se il browser può visualizzarne il formato. |
| Scarica | Recupera il file sul computer. |

Tipi e descrizioni uniformi migliorano i filtri dell'archivio cliente. La data mostrata è quella della registrazione nel WMS. Un allegato caricato durante un salvataggio intermedio resta nel fascicolo e può essere associato al risultato conclusivo dell'attività.

## 14. Amministrazione — Struttura comune
Aprire il ruolo Amministratore WMS. La pagina Configurazione contiene le linguette Utenti, Gruppi, Appartenenze, Politiche di assegnazione, Tipi di pratica, Clienti e Pratiche.

| Elemento | Uso |
|---|---|
| Titolo e contatore | Categoria selezionata e numero di elementi configurati. |
| Cerca in… | Ricerca nei campi visualizzati della categoria. |
| + Nuovo | Apre l'inserimento dell'elemento della categoria. Per le pratiche compare + Nuova pratica. |
| Modifica | Apre la scheda di un elemento esistente. |
| Stato | Attivo/Disattivo per la configurazione; stato del flusso per le pratiche. |
| Elimina | Chiede conferma ed elimina l'elemento se i controlli lo consentono. Non equivale a Disattivo. |
| Attivo | Casella nelle schede di configurazione. Le nuove pratiche propongono clienti e modelli attivi. |
| Salva modifiche | Registra i dati; nei modelli pubblica la configurazione. |
| Annulla / × | Chiude la scheda; per i tipi di pratica la chiusura conserva invece la bozza. |
| Messaggio di errore | Indica il campo o vincolo che impedisce il salvataggio. Correggere e ripetere. |

Gli ID esistenti sono in sola lettura. Il simbolo * evidenzia alcuni campi obbligatori, ma esistono anche controlli del server: assenza dell'asterisco non garantisce che un dato possa essere vuoto.
Non tutte le relazioni sono protette allo stesso modo dalla cancellazione. Per un'anagrafica storicamente utilizzata è opportuno preferire la disattivazione quando compatibile con l'organizzazione dello studio.

## 15. Amministrazione — Utenti
| Campo | Compilazione e significato |
|---|---|
| ID | Identificatore obbligatorio e stabile dell'utente. Non modificabile nella scheda esistente. |
| Login | Nome usato per accedere. Deve essere univoco; se omesso, il server può ricavarlo dall'ID. È preferibile compilarlo esplicitamente. |
| Nome visualizzato | Nome leggibile mostrato nell'interfaccia; richiesto dal server. |
| Appartenenza predefinita | ID di una delle appartenenze dell'utente. Determina il contesto iniziale; può essere vuoto. Non inserire il nome del gruppo al posto dell'ID dell'appartenenza. |
| Attivo | Abilitazione dell'utente nell'anagrafica di accesso. |

Per configurare un utente: creare l'utente senza appartenenza predefinita, creare l'appartenenza, quindi tornare all'utente e indicare quell'ID come predefinito se necessario.
La scheda non contiene un campo per creare, impostare o reimpostare la password. La sola creazione anagrafica non completa la predisposizione delle credenziali; questa parte richiede la procedura tecnica prevista per l'installazione.
L'eliminazione di un utente con appartenenze viene impedita dal server.

## 16. Amministrazione — Gruppi
| Campo | Compilazione e significato |
|---|---|
| Codice | Identificatore obbligatorio del gruppo; stabile dopo la creazione. |
| Nome | Denominazione obbligatoria, ad esempio Contabili. |
| Ruolo | Amministratore, Decisore, Supervisore, Validatore o Operatore. Definisce le funzioni delle appartenenze al gruppo. |
| Attivo | Abilitazione del gruppo. |
| Colore | Assegnato automaticamente e mostrato in lista e nel grafo. Non è un campo di priorità o avanzamento. |

Le attività dei modelli si assegnano a gruppi con ruolo Operatore. Non si assegna una normale attività esecutiva al gruppo Supervisore.
Non è possibile eliminare un gruppo utilizzato da appartenenze o da attività dei modelli. Il messaggio invita a gestire le relazioni o disattivare il gruppo.

## 17. Amministrazione — Appartenenze
| Campo | Compilazione e significato |
|---|---|
| ID | Identificatore obbligatorio dell'appartenenza. |
| Utente | Selezione di un utente esistente. |
| Gruppo | Selezione di un gruppo esistente; il ruolo deriva da questo gruppo. |
| Etichetta | Testo obbligatorio per riconoscere il contesto nel menu Ruolo attivo, ad esempio Operatore · Contabili. |
| Attivo | Abilita o disabilita quella appartenenza. |

Un utente può avere più appartenenze, anche a più gruppi operatore. La scrivania mostra il lavoro del gruppo attivo, non la somma indistinta di tutti i gruppi dell'utente.

## 18. Amministrazione — Politiche di assegnazione
| Campo | Significato |
|---|---|
| Codice | ID obbligatorio della politica. |
| Nome | Nome descrittivo obbligatorio. |
| Strategia | Testo obbligatorio che identifica la strategia configurata. |
| Descrizione | Spiegazione libera del criterio organizzativo. |
| Attivo | Stato del record di configurazione. |

La versione verificata implementa la presa in carico volontaria delle attività del gruppo. Non risultano meccanismi nell'interfaccia operativa che applichino arbitrariamente nuove strategie inserite in questa tabella. Scrivere, ad esempio, una strategia di ripartizione automatica non rende disponibile tale automazione.

## 19. Amministrazione — Clienti
| Campo | Compilazione e significato |
|---|---|
| Codice cliente | Identificatore obbligatorio. È la chiave di collegamento fra pratiche e archivio documenti; per l'importazione è stato usato per deduplicare i clienti dei tre Excel. |
| Ragione sociale | Nome obbligatorio del cliente; per persone fisiche inserire il nominativo. |
| Codice fiscale | Dato anagrafico facoltativo nell'interfaccia corrente. |
| Partita IVA | Dato anagrafico facoltativo. |
| Email | Indirizzo email; il campo applica il controllo formale del browser. Non è un comando di invio. |
| Attivo | I clienti attivi vengono proposti nella creazione delle pratiche. |

La scheda non presenta campi per indirizzo, telefono o referente nella versione documentata. Non è prevista una funzione grafica di fusione di due clienti duplicati.

## 20. Amministrazione — Tipi di pratica: dati generali
Il tipo di pratica descrive il lavoro riutilizzabile. Le modifiche al modello si applicano alle nuove pratiche, non aggiornano automaticamente quelle già create.

| Campo | Compilazione e significato |
|---|---|
| ID | Identificatore del modello, obbligatorio e non modificabile dopo la creazione. |
| Codice | Codice del tipo mostrato nelle liste delle pratiche. Obbligatorio e univoco. |
| Nome | Denominazione leggibile del modello, obbligatoria. |
| Descrizione | Scopo e indicazioni generali del modello. |
| Attivo | Rende il modello selezionabile per creare nuove pratiche. |
| Richiede validazione finale | Se selezionato, alla fine del percorso la pratica va al validatore prima della chiusura del supervisore. |
| Dati generali | Linguetta con i campi appena descritti. |
| Attività | Linguetta con grafo ed elenco delle attività. Il contatore mostra quante attività sono nel modello. |

Un modello può contenere al massimo 200 attività. Non usare lo stesso codice per due attività dello stesso modello.

## 21. Editor del modello — Attività, campo per campo
La modifica può essere effettuata nel pannello laterale del grafo oppure nella scheda espandibile sotto il grafo. Si tratta degli stessi dati.

| Campo o comando | Regola ed effetto |
|---|---|
| + Aggiungi attività | Crea una nuova attività da completare con codice, titolo e responsabilità. |
| Codice attività | Obbligatorio e univoco nel modello. @END è riservato. La rinomina passa dal comando di modifica del campo per aggiornare i riferimenti del disegno. |
| Titolo | Nome obbligatorio che l'operatore vedrà nella scrivania. Deve descrivere il lavoro. |
| Gruppo responsabile | Selezione obbligatoria di un gruppo con ruolo Operatore. |
| Giorni prima della scadenza | Numero intero da 0 a 3650. La data attività viene calcolata sottraendo questi giorni alla scadenza della pratica alla sua creazione. |
| Nodo iniziale | Attiva l'attività all'apertura della pratica. Più caselle selezionate significano più attività iniziali in parallelo. |
| Istruzioni / Istruzioni operative | Spiegazione del lavoro, dei controlli e degli eventuali documenti da allegare. |
| Esito | Nome del risultato selezionabile e collegabile a una o più destinazioni. I nomi devono essere distinti nell'attività. |
| + Esito / + Aggiungi esito | Aggiunge una scelta di risultato. |
| Destinazioni | Attività da attivare quando si registra quell'esito. Più destinazioni dello stesso esito avviano più rami. |
| Fine ramo (@END) | Termina il ramo; anche nessuna destinazione rappresenta una fine ramo. Non chiude automaticamente la pratica. |
| Rimuovi esito | Elimina la scelta dal modello in modifica. |
| Sposta su / Sposta giù | Cambia l'ordine visivo dell'elenco; non cambia la sequenza operativa definita dalle frecce. |
| Rimuovi attività | Rimuove il nodo dalla configurazione in modifica. Verificare collegamenti e diagnostica prima di pubblicare. |

Esempio di scadenza relativa: pratica con scadenza 20 ottobre e attività con 10 giorni di anticipo → scadenza attività 10 ottobre. Nella schermata corrente non è presente una regola autonoma “16 giugno di ogni anno” per il singolo nodo. I termini fissi discussi per IMU V2 non devono quindi essere considerati automaticamente configurati.

### 21.1 Esiti alternativi e attività parallele
Due esiti diversi possono portare a due percorsi alternativi: “PAGA IN UNICA SOLUZIONE” e “PAGA IN DUE RATE”, per esempio.
Un solo esito con due destinazioni attiva invece entrambe le attività: non sceglie una delle due.
L'esito speciale * rappresenta la transizione generale/predefinita, usata quando non c'è una transizione specifica per l'esito registrato. Non è una richiesta all'operatore di digitare un asterisco.
Le frecce in ingresso non costituiscono, da sole, una regola esplicita di attesa di tutti i rami precedenti. Non progettare una convergenza assumendo una sincronizzazione automatica non indicata nell'interfaccia.
Il modello deve essere aciclico: non sono ammessi collegamenti che creino un ciclo. Per correggere lavoro già svolto si usano le funzioni di riapertura/sanatoria.

## 22. Editor grafico — Comandi e legenda
| Comando | Uso |
|---|---|
| Doppio clic sullo sfondo | Aggiunge un'attività nel punto scelto, in modalità progettazione. |
| Clic sul nodo o titolo attività | Apre il pannello laterale di modifica. |
| Trascinamento dal titolo | Sposta il nodo; modifica la disposizione del disegno, non la logica. |
| Uscita dell'esito → ingresso attività | Disegna un collegamento fra le due fasi. |
| + Attività nel grafo | Aggiunge un nodo nell'area del grafo. |
| + Collegamento | Apre la scheda esplicita di collegamento. |
| Modifica [codice] | Collegamento alternativo per aprire il pannello del nodo. |
| − / + | Riduce o ingrandisce il grafo. |
| Adatta | Riporta l'intero grafo nell'area visibile. |
| Disponi automaticamente | Riorganizza le posizioni dei nodi. |
| × del pannello attività | Chiude il pannello, senza pubblicare il modello. |

### 22.1 Scheda collegamento
| Campo o comando | Significato |
|---|---|
| Da attività | Nodo di partenza. |
| Esito (* = qualsiasi) | Risultato che attiva il collegamento, oppure regola generale. |
| A attività | Destinazione; può essere Fine ramo. |
| Applica collegamento | Applica la modifica al disegno in lavorazione. Non sostituisce Salva modifiche del modello. |
| Rimuovi collegamento | Disponibile modificando un collegamento esistente. |
| Annulla collegamento | Chiude l'editor del collegamento senza applicare quella modifica. |

### 22.2 Colori e segnalazioni
| Indicatore | Significato |
|---|---|
| Fondino azzurro | Nodo iniziale. |
| Fondino rosato | Nodo finale. |
| Fondino viola | Attività con più esiti. |
| Fondino a fasce | Nodo con più caratteristiche. |
| Colore dell'intestazione del nodo | Gruppo responsabile, secondo la legenda. |
| Freccia tratteggiata | Fine ramo implicita. |
| Attenzione: più nodi iniziali | Avviso di avvio parallelo; verificare che sia intenzionale. |
| Controlla i collegamenti | Diagnostica di collegamenti o raggiungibilità. Alcune segnalazioni consentono di salvare il modello ma richiedono correzione prima di creare una pratica. |

### 22.3 Grafo di una pratica già creata
È una vista di consultazione. Cliccare il nodo apre l'attività.
Bordo verde: completata. Bordo blu: attiva. Bordo grigio: non raggiunta. Le frecce verdi mostrano il percorso attraversato.
Questi colori hanno una legenda diversa dai bordini delle liste: nel grafo verde significa completamento del nodo, mentre nelle liste indica l'assenza delle condizioni di attenzione previste per quella riga.

## 23. Bozze e pubblicazione dei modelli
| Elemento | Uso |
|---|---|
| Stato della bozza | Indica se il disegno è salvato sul server o se il salvataggio ha avuto un problema. |
| Salva modifiche | Pubblica il modello. Le nuove pratiche useranno la versione pubblicata. |
| Chiudi e conserva bozza | Chiude la finestra conservando il lavoro non pubblicato. |
| Bozze recuperabili | Elenco dei disegni salvati, con nome e data/ora. Le bozze sono legate all'utente che le ha create. |
| Riprendi bozza | Riapre il disegno per continuare a modificarlo. |
| Elimina bozza | Elimina la bozza dopo conferma, senza modificare il modello pubblicato. |
| Riprova salvataggio | Ripete il salvataggio quando il sistema segnala un problema. |
| Salva una copia della bozza | Crea un'altra bozza sul server per recuperare il lavoro; non è un download del modello. |
| Riaccedi e scegli Amministratore in un'altra scheda | Permette di recuperare una sessione senza abbandonare subito il disegno aperto. |

Il salvataggio automatico delle bozze riguarda l'editor dei tipi di pratica, non tutte le caselle dell'applicazione. Per note di lavoro, allegati e anagrafiche utilizzare i rispettivi pulsanti di salvataggio.
Se compare Bozza non salvata, mantenere aperta la pagina e seguire i comandi di recupero. Non interpretare il solo disegno visibile come prova che il modello sia stato pubblicato.

## 24. Amministrazione — Pratiche cliente
La tabella elenca Codice, Cliente, Tipo, Dal, Al, Scadenza e Stato. Il pulsante Attività apre un riepilogo. La scheda non offre i normali pulsanti Modifica/Elimina previsti per le anagrafiche.

### 24.1 Nuova pratica
| Campo | Regola |
|---|---|
| Cliente | Obbligatorio; selezionare un cliente attivo. |
| Modello | Obbligatorio; selezionare un tipo di pratica attivo. |
| Inizio periodo | Data iniziale del riferimento, obbligatoria. |
| Fine periodo | Data finale del riferimento, obbligatoria. Deve essere coerente con l'inizio. |
| Scadenza pratica | Termine operativo della pratica, obbligatorio. |
| Crea pratica | Genera il codice della pratica e copia attività, istruzioni, assegnazioni e regole dal modello. |
| Annulla | Chiude senza creare la pratica. |

Prima di creare verificare cliente, periodo, modello e scadenza. Il periodo non stabilisce automaticamente la scadenza e non implica una scadenza fiscale corretta. Non assumere che il programma impedisca ogni duplicazione organizzativa dello stesso adempimento.

### 24.2 Finestra Attività della pratica
| Colonna o comando | Contenuto |
|---|---|
| Attività | Codice, titolo e istruzioni. |
| Gruppo | Responsabile organizzativo. |
| Scadenza | Data calcolata del task oppure scadenza pratica. |
| Percorso | Esiti e destinazioni; Fine in assenza di uscite. |
| Stato | Stato del task o Non raggiunta. |
| Apri fascicolo completo | Apre il dettaglio generale della pratica. |
| Chiudi / × | Chiude il riepilogo. |

## 25. Esempi completi d'uso
### 25.1 Dal lavoro alla chiusura
1. L'amministratore crea la pratica per il cliente, scegliendo modello, periodo e scadenza.
2. Gli operatori vedono soltanto le attività inizialmente eseguibili.
3. L'operatore salva il lavoro intermedio oppure completa con esito.
4. Il sistema attiva le fasi successive secondo il modello.
5. Quando tutti i nodi raggiunti sono completati, la pratica è Completata o Da validare.
6. Se prevista, un validatore diverso dagli esecutori registra la decisione.
7. Il supervisore verifica il fascicolo e registra la chiusura.
8. La pratica si consulta nello Storico e i documenti restano nel catalogo cliente.

### 25.2 Correzione richiesta dal validatore
1. Il validatore sceglie Non validata e motiva.
2. Il supervisore apre la non conformità, seleziona le attività e scrive le istruzioni.
3. Avvia sanatoria riapre le attività.
4. Gli operatori leggono la motivazione e registrano il lavoro corretto.
5. La pratica torna alla validazione.
6. La verifica positiva chiude la non conformità; il supervisore può poi chiudere la pratica.

### 25.3 Ricerca di un documento cliente
1. Selezionare Supervisore → Documenti clienti.
2. Cercare il cliente per nome o codice e selezionarlo.
3. Scegliere il tipo documento, cercare una parola della descrizione o selezionare la provenienza.
4. Leggere periodo e pratica per evitare di usare il documento di un altro esercizio.
5. Aprire/scaricare il file oppure aprire il fascicolo di origine.

### 25.4 Progettazione di un percorso alternativo
1. Creare il tipo e compilare i dati generali.
2. Aggiungere il nodo iniziale, ad esempio Calcolo.
3. Collegare un nodo di scelta operativa con esiti distinti.
4. Collegare ciascun esito al proprio ramo.
5. Definire gruppo, istruzioni e anticipo di scadenza per ogni fase.
6. Verificare che le attività siano raggiungibili e non esistano cicli.
7. Pubblicare con Salva modifiche.
8. Creare una pratica TEST e verificare il percorso prima di usarlo sistematicamente.

## 26. Messaggi e casi frequenti
| Situazione | Come interpretarla e intervenire |
|---|---|
| Nessuna attività da lavorare | Verificare il gruppo attivo, i filtri e Aggiorna; il lavoro potrebbe essere futuro, completato o in carico a colleghi. |
| Attività occupata | Un collega ha acquisito il task. Il supervisore può valutare una riassegnazione quando consentita. |
| Non vedo una pratica completata nell'operatore | La scrivania operatore mostra lavoro e completamenti personali recenti, non l'intero archivio. Usare lo storico supervisore. |
| Non compare Chiusa nel filtro Stato | Non ci sono pratiche chiuse nell'insieme caricato. Le opzioni derivano dagli stati presenti. |
| Pratica al 100% ma ancora attiva | Attende validazione o chiusura formale. |
| Percentuale cambiata dopo un completamento | Sono state raggiunte nuove attività e il denominatore è cresciuto. |
| Modifica al modello non presente nelle vecchie pratiche | Le pratiche copiano il modello alla creazione; le modifiche successive valgono per nuove istanze. |
| Non posso cambiare ramo dopo riapertura | Il sistema protegge il percorso già attraversato; la correzione non può cambiare le destinazioni precedenti. |
| Non posso validare | Controllare stato Da validare, completamento delle attività, nota richiesta e separazione fra esecutore e validatore. |
| Non posso chiudere | Verificare stato, eventuale validazione richiesta e non conformità aperte. |
| Documento non presente nell'archivio cliente | Una nota che cita un file non equivale a un allegato; verificare che il documento sia stato effettivamente salvato nella pratica. |
| Più categorie quasi identiche | Tipo documento è libero: uniformare i nomi nei nuovi caricamenti. Non è disponibile una riclassificazione massiva dalla vista cliente. |
| File superiore a 5 MB | Preparare una versione più piccola o suddividere il documento secondo le procedure dello studio. |
| Connessione non disponibile | Riprovare quando il servizio torna raggiungibile, verificando l'esito dell'operazione prima di ripeterla. |
| La versione dell'interfaccia è cambiata | Ricaricare la pagina dopo aver verificato eventuale lavoro non salvato. |
| Bozza non salvata | Mantenere aperto l'editor, recuperare la sessione e usare Riprova salvataggio o Salva una copia. |
| Campo obbligatorio non evidenziato | Alcune verifiche avvengono sul server: leggere il messaggio e completare il dato. |

## 27. Riferimento degli stati
| Oggetto | Stato | Significato |
|---|---|---|
| Pratica | Da fare | Creata; lavorazione non ancora avviata. |
| Pratica | In corso | Percorso operativo avviato o riaperto. |
| Pratica | Completata | Tutte le attività raggiunte completate; senza validazione è pronta alla chiusura. |
| Pratica | Da validare | Attende la decisione del validatore. |
| Pratica | Validata | Decisione positiva registrata; attende chiusura. Un risultato con rilievi conserva i rilievi nell'esito. |
| Pratica | Non validata | Decisione negativa; richiede gestione della correzione. |
| Pratica | Chiusa | Chiusura finale registrata dal supervisore. |
| Attività | Da fare | Nodo lavorabile non ancora avviato, se attivo. |
| Attività | In corso | Lavoro salvato o riaperto. |
| Attività | Completata | Risultato registrato. |
| Attività | Non raggiunta | Nodo del modello non ancora attivato dal percorso. |
| Etichetta operativa | Riaperta | Task con motivo di riapertura; non è un nuovo tipo di pratica. |
| Etichetta operativa | Occupata | Presa in carico da un altro operatore. |
| Non conformità | Aperta | Correzione da definire. |
| Non conformità | In sanatoria | Azione correttiva in esecuzione. |
| Non conformità | Da verificare | Correzioni completate, attesa verifica. |
| Non conformità | Chiusa | Verifica positiva registrata. |

## 28. Limiti della versione e criteri di lettura
Questo manuale descrive la release 1.4.1, non funzionalità future. In particolare:
- Le scadenze delle attività sono relative alla scadenza della pratica; non c'è una schermata per ricorrenze fiscali fisse per nodo.
- I documenti sono allegati manualmente nelle operazioni; non sono prodotti automaticamente dai nomi delle attività.
- Storico supervisore e viste delle ultime otto ore hanno scopi e coperture differenti.
- La gestione password non è disponibile nella scheda Utenti.
- Il ruolo Decisore non dispone di una scrivania dedicata.
- Le politiche anagrafiche non aggiungono da sole nuove automazioni di assegnazione.
- Le modifiche del modello non migrano le pratiche già create.
- Non è disponibile un comando ordinario per riaprire una pratica chiusa.
- Non sono presenti in queste schermate ricerca nel contenuto dei file, esportazione massiva o modifica dei metadati degli allegati già registrati.
- I filtri dello storico e la selezione cliente sono strumenti della vista; non costituiscono ricerche salvate permanenti.

Per leggere un dato importato dai fogli Excel, distinguere sempre il valore originale conservato nella nota dalla data in cui il WMS ha registrato l'importazione. Il verde del foglio sorgente ha indicato le attività eseguite; il verde dei bordini dell'interfaccia segue invece la legenda specifica della schermata.

## 29. Indice rapido per operazione
| Devo… | Dove andare |
|---|---|
| Eseguire un'attività | Operatore → Da lavorare → Apri/Riprendi |
| Salvare lavoro non finito | Dettaglio operatore → Salva e torna ai compiti |
| Registrare il risultato | Dettaglio operatore → Esito → Registra risultato e completa |
| Vedere lavoro riservato ai colleghi | Operatore → In carico ai colleghi |
| Controllare una pratica | Supervisore → Pratiche attive → collegamento pratica |
| Cercare pratiche passate | Supervisore → Storico |
| Trovare tutti i documenti del cliente | Supervisore → Documenti clienti |
| Riassegnare un'attività | Fascicolo → dettaglio attività → Gruppo assegnatario |
| Riaprire una fase | Fascicolo → dettaglio attività → Motivo → Riapri task |
| Gestire una validazione negativa | Fascicolo → Non conformità → Avvia sanatoria |
| Validare | Validatore → Pratiche da validare → fascicolo |
| Chiudere definitivamente | Supervisore → fascicolo → Chiusura pratica |
| Creare un cliente | Amministratore → Clienti → Nuovo |
| Creare un modello | Amministratore → Tipi di pratica → Nuovo |
| Riprendere un disegno non pubblicato | Amministratore → Bozze recuperabili |
| Aprire una nuova pratica cliente | Amministratore → Pratiche → Nuova pratica |
| Ricostruire chi ha fatto cosa | Fascicolo → Archivio completo → Audit |

## Nota editoriale
Manuale redatto il 21 settembre 2026 sulla release TEST 1.4.1. Per futuri aggiornamenti confrontare il numero di release nella testata con quello riportato in copertina. La preparazione del manuale non modifica programmi, pratiche, utenti o documenti dell'applicazione.
