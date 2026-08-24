# Tests

Test del motore WMS.

Primi scenari obbligatori:

- creazione pratica da template
- generazione task
- rifiuto transizioni di stato non consentite
- passaggio automatico a DA_VALIDARE quando previsto
- validazione consentita solo a ruolo autorizzato
- audit event generato per ogni transizione
