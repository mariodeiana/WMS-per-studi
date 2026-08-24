from .models import Task


LIPE_TRIM_TASKS = [
    ("LIPE-01", "Verifica disponibilità dati del periodo", "Verifica che tutti i dati IVA del trimestre siano disponibili."),
    ("LIPE-02", "Controllo completezza registrazioni IVA", "Controlla completezza e coerenza delle registrazioni IVA."),
    ("LIPE-03", "Elaborazione dati LIPE", "Elabora i dati LIPE usando le fonti disponibili nel fascicolo."),
    ("LIPE-04", "Controllo risultato elaborazione", "Confronta il risultato elaborato con registri e liquidazioni."),
    ("LIPE-05", "Predisposizione invio", "Predisponi il file e documenta i controlli preliminari all'invio."),
    ("LIPE-06", "Verifica esito / ricevuta", "Verifica l'esito e allega la ricevuta disponibile."),
    ("LIPE-07", "Completamento operativo", "Esegui il controllo finale e riepiloga l'attività svolta."),
]


def build_lipe_trim_tasks() -> list[Task]:
    return [Task(code=code, title=title, instructions=instructions) for code, title, instructions in LIPE_TRIM_TASKS]
