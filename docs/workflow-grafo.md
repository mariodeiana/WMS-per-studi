# Workflow a grafo orientato

Ogni Tipo pratica contiene i suoi nodi attività. Il codice del nodo identifica
l'origine della mappa `transitions`: nessun catalogo di nodi o subworkflow.

```json
{
  "code": "A",
  "title": "Controllo iniziale",
  "assigned_group": "contabili",
  "outcomes": ["OK", "KO"],
  "transitions": {"OK": ["B", "C"], "KO": ["@END"]}
}
```

Ogni voce equivale a `from_activity + outcome + to_activity`. La chiave `*`
indica una prosecuzione predefinita per qualsiasi esito; una voce per un esito
specifico la sostituisce, anche quando contiene una lista vuota. Non esiste un
linguaggio di condizioni: la condizione è l'esito registrato dall'operatore.
`*` non è un esito selezionabile dall'operatore.

- All'apertura sono raggiunti solo i nodi marcati esplicitamente `is_initial`.
  I modelli preesistenti ricevono questa scelta sui precedenti nodi senza ingressi. L'ordine delle
  righe e i giorni alla scadenza non influiscono sul percorso.
- Completare un nodo attiva tutte le destinazioni dell'esito scelto.
- Nessuna transizione, una lista vuota o `@END` termina quel ramo. Non annulla
  altri rami: tutti i nodi raggiunti devono essere completati, anche se un vecchio
  modello li marcava facoltativi.
- Il completamento operativo porta a COMPLETATA o DA_VALIDARE. Restano la
  validazione, le non conformità e la chiusura esplicita del supervisore.
- Una convergenza attiva il nodo una sola volta al primo arrivo (OR). Non è una
  barriera di sincronizzazione AND; gli altri rami proseguono e impediscono la
  conclusione prematura della pratica.

## Istanza e scrivanie

La pratica copia il grafo al momento della creazione: successive modifiche al
Tipo pratica non cambiano le istanze. Il campo storico `active` indica un nodo
raggiunto e rimane vero dopo il completamento. Un nodo eseguibile è raggiunto,
non completato e appartiene a una pratica DA_FARE o IN_LAVORAZIONE.

Le scrivanie operatore filtrano i nodi eseguibili; i completati recenti restano
in una sezione storica separata. Il supervisore vede conteggi e attività del
percorso raggiunto. La percentuale misura completati/raggiunti, non una stima del
lavoro futuro: il denominatore cresce all'attivazione di nuovi nodi.

La scheda conserva il grafo completo, distinguendo i nodi non raggiunti dal
lavoro da fare. Risultati e audit conservano il percorso effettivo, gli esiti,
gli autori, i documenti e le transizioni scelte.

## Migrazione e limiti deliberati

I demo LIPE, F24, riconciliazione, CU e bilancio sono sequenze in avanti. La
migrazione di catalogo `workflow_version=1` è idempotente: concatena solo i demo
senza transizioni o prerequisiti, preservando i modelli già personalizzati.
Le pratiche salvate mantengono il proprio snapshot: per provare il nuovo demo
creare nuove pratiche. Le configurazioni con prerequisiti devono essere
ridisegnate in transizioni; il backend le rifiuta, evitando conversioni ambigue.
I prerequisiti restano leggibili nelle vecchie istanze e ne filtrano l'eseguibilità.

La UI usa Supervisore. Il codice di ruolo `MANAGER`, gli identificativi delle
appartenenze e gli URL esistenti restano invariati.

I cicli sono rifiutati. Una correzione può riaprire nodi completati ma non cambiare
le destinazioni già attraversate, né eseguire nuovamente i successori completati.
Restano da definire, se necessari: cicli con più occorrenze dello stesso nodo,
join AND, annullamento globale dei rami e cambio di percorso dopo una correzione.

## Grafo interattivo Angular

Il componente condiviso `WorkflowGraph`, basato su Foblex Flow 19, è presente
nella scheda pratica e nella scheda Attività dell'editor dei Tipi pratica.

- Nella pratica: nodi verdi completati, blu attivi, grigi non raggiunti; i
  collegamenti attraversati sono verdi. Il pulsante sul nodo apre il dettaglio.
  Il grafo è in consultazione e non cambia le regole né l'avanzamento.
- Nel Tipo pratica: aggiungere un'attività, spostarla dalla sua intestazione,
  trascinare dall'uscita etichettata dell’esito all'ingresso di un altro nodo.
  Ogni esito ha una propria uscita; dalla stessa uscita si possono creare più
  archi per attivare attività parallele. Il trascinamento preseleziona l’esito.
  Le transizioni `*` conservano un’uscita predefinita esplicita.
  Il pannello del collegamento permette di impostare origine, esito e
  destinazione; lo stesso pannello è accessibile dal pulsante Collegamento
  o dalle etichette sulle frecce. Applica modifica la bozza; Salva modifiche
  registra l'intero modello. La rimozione dell'ultima destinazione lascia la
  fine implicita del ramo per quell'esito.
- I dettagli di gruppo, istruzioni, scadenza ed esiti restano modificabili
  sotto il grafo e restano sincronizzati con il disegno.
- Zoom con i pulsanti oppure Ctrl/Cmd + rotella; la normale rotella scorre la
  pagina. Adatta mostra il grafo completo. Disponi automaticamente elimina
  le posizioni manuali della bozza, senza cambiare le transizioni.

Le coordinate opzionali `graph_position: {x, y}` appartengono al singolo nodo:
sono validate, salvate nel modello e copiate nella pratica quando viene creata.
Le istanze e i modelli preesistenti senza coordinate usano una disposizione
automatica per livelli. I rami con più predecessori seguono la stessa semantica
OR del motore. Le frecce tratteggiate indicano finali impliciti, non dipendenze.

## Ambiente di lavoro e pubblicazione

Sviluppo, compilazione, test e anteprime devono usare le risorse di
ASC-OLB-WFO-01. Il repository è `/opt/asc/wms/WMS-per-studi` e il DEV
pubblicato è `http://192.168.1.23:8000`.
Il grafo di design si trova in Configurazione → Tipi di pratica → Attività;
il grafo del percorso si trova nella scheda della pratica.

Rilascio DEV del 19 settembre 2026: 74 test backend e 32 test Angular superati
sul server, build Angular e Docker riuscite. Verificata lettura e serializzazione
di tutte le 25 pratiche esistenti su copia dei dati; dopo il rilascio verificati
health, ambiente DEV e rendering Angular con Chrome sul server.
Backup sorgenti e dati: `/opt/asc/wms/backups/graph-20260919-222035`.
Immagine precedente: `asc-wms:before-graph-dev`. TEST e PROD non aggiornati.

## Verifica dei nodi scollegati

Nel designer la casella «Nodo iniziale» identifica gli avvii intenzionali.
Le segnalazioni distinguono assenza di avvii, nodi senza ingressi non iniziali
e nodi non raggiungibili da alcun avvio. Tutti gli esiti sono considerati nella
verifica: un ramo alternativo valido non è orfano. I nodi terminali sono leciti.
Il modello incompleto si può salvare, ma non generare pratiche finché restano
segnalazioni. La migrazione mantiene gli avvii dei modelli esistenti e non modifica
le pratiche già create.

## Progettazione dal grafo e bozze

Doppio clic sullo sfondo del grafo oppure «Attività nel grafo» crea un nodo.
Il pannello laterale modifica gli stessi dati della lista sottostante: codice,
titolo, gruppo, anticipo scadenza, istruzioni, avvio iniziale ed esiti. Trascinare
un’uscita su un ingresso apre il collegamento con l’esito preselezionato;
l’etichetta dell’arco permette modifica e rimozione.

Le modifiche dell’editor sono salvate circa ogni secondo come bozze private
per utente in `/data/.wms-model-drafts`, con sostituzione atomica e controllo
della revisione. La bozza può contenere dati ancora incompleti e collegamenti
non applicati; non cambia i modelli pubblicati o le pratiche esistenti.
«Chiudi e conserva bozza» attende il salvataggio. «Riprendi bozza» recupera i
dati dal server dopo una nuova autenticazione o il riavvio dell’applicazione.
«Salva modifiche» valida e pubblica il modello, poi elimina la bozza pubblicata.
Una bozza non può sovrascrivere un modello pubblicato cambiato nel frattempo.

Se il server non è disponibile o la sessione scade, lo stato segnala chiaramente
che la bozza non è stata salvata; mantenere aperta la pagina e riaccedere come
amministratore in un’altra scheda. Il browser avverte prima di lasciare la pagina
con modifiche non ancora salvate. Non si può garantire il recupero di modifiche
mai ricevute dal server se la pagina viene comunque chiusa. Non si usa memoria
persistente locale del browser per conservare le bozze.
