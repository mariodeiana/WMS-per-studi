from .models import Task


LIPE_TRIM_TASKS = [
    ("LIPE-01", "Verifica disponibilità dati del periodo"),
    ("LIPE-02", "Controllo completezza registrazioni IVA"),
    ("LIPE-03", "Elaborazione dati LIPE"),
    ("LIPE-04", "Controllo risultato elaborazione"),
    ("LIPE-05", "Predisposizione invio"),
    ("LIPE-06", "Verifica esito / ricevuta"),
    ("LIPE-07", "Completamento operativo"),
]


def build_lipe_trim_tasks() -> list[Task]:
    return [Task(code=code, title=title) for code, title in LIPE_TRIM_TASKS]
