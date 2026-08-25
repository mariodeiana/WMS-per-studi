from .models import Task


LIPE_TRIM_TASKS = [
    ("LIPE-01", "Verifica disponibilità dati del periodo", "Verifica che tutti i dati e i documenti necessari del periodo siano disponibili. Registra eventuali mancanze nelle note e allega le evidenze utili."),
    ("LIPE-02", "Controllo completezza registrazioni IVA", "Controlla la completezza delle registrazioni IVA del periodo e documenta eventuali anomalie o elementi da integrare."),
    ("LIPE-03", "Elaborazione dati LIPE", "Esegui l'elaborazione dei dati LIPE utilizzando il materiale validato nelle fasi precedenti. Allega gli output rilevanti."),
    ("LIPE-04", "Controllo risultato elaborazione", "Controlla il risultato dell'elaborazione e confrontalo con i dati disponibili. Registra rilievi ed evidenze."),
    ("LIPE-05", "Predisposizione invio", "Predisponi il materiale necessario all'invio e verifica che il fascicolo contenga gli elementi richiesti."),
    ("LIPE-06", "Verifica esito / ricevuta", "Verifica l'esito dell'invio e acquisisci la ricevuta o altra evidenza disponibile."),
    ("LIPE-07", "Completamento operativo", "Verifica che le attività operative siano complete e che le evidenze necessarie siano presenti prima di dichiarare concluso il task."),
]


def build_lipe_trim_tasks() -> list[Task]:
    return [Task(code=code, title=title, instructions=instructions) for code, title, instructions in LIPE_TRIM_TASKS]
