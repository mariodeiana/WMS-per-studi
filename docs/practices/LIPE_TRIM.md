# LIPE_TRIM — pratica pilota WMS Core v0.1

## Scopo

Usare la Comunicazione delle liquidazioni periodiche IVA come primo workflow completo del motore WMS.

## Natura

- Frequenza: trimestrale
- Istanza: una pratica per Cliente + periodo
- Validazione finale: prevista

## Template task iniziale

1. Verifica disponibilità dati del periodo
2. Controllo completezza registrazioni IVA
3. Elaborazione dati LIPE
4. Controllo risultato elaborazione
5. Predisposizione invio
6. Verifica esito / ricevuta
7. Completamento operativo
8. Validazione responsabile

Questo template è volutamente iniziale: i task saranno raffinati con l'analisi operativa reale dello studio.

## Workflow

`DA_FARE -> IN_LAVORAZIONE -> COMPLETATA -> DA_VALIDARE -> VALIDATA -> CHIUSA`

### Regole

- `DA_FARE -> IN_LAVORAZIONE`: almeno un task viene preso in carico.
- `IN_LAVORAZIONE -> COMPLETATA`: tutti i task operativi obbligatori sono completati.
- `COMPLETATA -> DA_VALIDARE`: automatico se il tipo richiede validazione.
- `DA_VALIDARE -> VALIDATA`: solo ruolo autorizzato.
- `VALIDATA -> CHIUSA`: chiusura formale della pratica.
- Ogni transizione genera un evento di audit.

## Dati minimi della pratica

- id
- practice_type_code = LIPE_TRIM
- client_id
- period_start
- period_end
- due_date
- status
- assigned_team / owner
- created_at
- updated_at
- validated_by
- validated_at

## Criterio di successo v0.1

Il sistema deve riuscire a creare una LIPE da template, generare i task, farli avanzare, impedire transizioni non valide, richiedere la validazione finale e produrre una cronologia audit completa.
