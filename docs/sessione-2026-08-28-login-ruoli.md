# Sessione 28 agosto 2026 — Login, gruppi e ruolo attivo

## Decisioni di modello

- Un utente non riceve direttamente i task.
- I task saranno assegnati ai gruppi già in fase di progettazione del modello di pratica.
- Ogni gruppo appartiene a un solo ruolo.
- Un utente può appartenere a più gruppi e quindi disporre di più contesti operativi/ruoli.
- Al login viene attivata l'appartenenza predefinita dell'utente.
- Se l'utente possiede più appartenenze può selezionare un altro contesto operativo e cambiarlo durante la sessione senza logout.
- Il menu deve mostrare l'appartenenza operativa, non solo il ruolo generico: per esempio `Operatore · Contabili` e `Operatore · Segreteria`.
- La futura assegnazione dal gruppo al singolo esecutore (dispatch) è un problema separato. Potrà essere manuale/self-pick o algoritmica.

## Prima implementazione

Il branch `dev/session-28-aug-login-role` introduce:

- schermata di login;
- sessione HTTP tramite cookie `WMSSESSION`;
- directory demo di utenti e appartenenze;
- appartenenza predefinita;
- endpoint per leggere la sessione e cambiare appartenenza attiva;
- selettore del contesto operativo nella topbar;
- cambio scrivania automatico in base al ruolo attivo;
- logout;
- API applicative che ricavano l'actor dalla sessione anziché fidarsi dei parametri `actor`/`operator` inviati dal client.

## Utenti demo

- `mario.demo / demo`: Manager (predefinito) oppure Operatore · Contabili.
- `valeria.demo / demo`: Validatore · Contabili.
- `luca.demo / demo`: Operatore · Contabili.

## Ponte temporaneo con il modello precedente

Il workflow esistente associa ancora il ruolo a identificativi tecnici come `marta.manager`, `anna.operatore`, `valeria.validatore`. La sessione nuova separa già l'utente reale dal contesto attivo, ma usa temporaneamente questi actor tecnici per invocare il workflow esistente.

Questo ponte dovrà essere rimosso quando verranno introdotti nel core `User`, `Group`, `Membership` e l'assegnazione del task al gruppo. L'audit definitivo dovrà registrare almeno: utente reale, ruolo attivo, gruppo attivo, timestamp e azione.

## Passo successivo

Portare nel core i concetti di `User`, `Role`, `Group`, `Membership` e sostituire l'assegnazione individuale dei task con `assigned_group_id`. L'eventuale `assigned_user_id` sarà separato e opzionale, destinato al futuro meccanismo di dispatch/presa in carico.
