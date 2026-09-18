# Clienti, modelli e nuove pratiche

Accedere come **Amministratore WMS** alla pagina **Configurazione**.

- **Clienti → Nuovo**: codice stabile, nome/ragione sociale, codice fiscale, partita IVA, email e stato attivo. I clienti già citati dalle pratiche vengono recuperati automaticamente: inizialmente il nome coincide con il codice e può essere completato con Modifica.
- **Tipi di pratica → Modifica**: anagrafica del modello, validazione finale e attività. Ogni attività ha codice, titolo, istruzioni, gruppo operatore, obbligatorietà, dipendenze e giorni di anticipo rispetto alla scadenza della pratica. Sposta su/giù cambia l'ordine visivo; le dipendenze regolano il completamento. Il sistema rifiuta cicli, codici duplicati e riferimenti inesistenti.
- **Pratiche → Nuova pratica**: scegliere cliente e modello attivi, periodo e scadenza. Il sistema genera un codice univoco e copia le attività dal modello. Attività consente di controllare la copia creata; la pratica compare nella scrivania Manager e le attività nelle code dei gruppi assegnati.

Le modifiche successive ai modelli non cambiano le pratiche già create. Clienti e modelli utilizzati non possono essere eliminati; possono essere disattivati. Il codice di un modello utilizzato non può cambiare.

La configurazione resta in `.wms-config.json`; le pratiche e lo storico restano in `.wms-demo-state.pkl`. Al primo avvio vengono aggiunti i modelli demo mancanti, senza cancellare quelli personalizzati. Anche la precedente voce LIPE viene mantenuta. Le scadenze delle attività già esistenti continuano a usare la scadenza della pratica.

La selezione del gruppo usa i gruppi operatore configurati. L'accesso degli utenti continua a usare il sistema demo preesistente: la gestione completa di credenziali e nuove identità non fa parte di questa modifica.
