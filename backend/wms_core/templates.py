from .models import Task


PRACTICE_TEMPLATES = {
    "LIPE_TRIM": [
        ("LIPE-01", "Verifica disponibilità dati del periodo", "Verifica che tutti i dati e i documenti necessari del periodo siano disponibili. Registra eventuali mancanze nelle note e allega le evidenze utili."),
        ("LIPE-02", "Controllo completezza registrazioni IVA", "Controlla la completezza delle registrazioni IVA del periodo e documenta eventuali anomalie o elementi da integrare."),
        ("LIPE-03", "Elaborazione dati LIPE", "Esegui l'elaborazione dei dati LIPE utilizzando il materiale validato nelle fasi precedenti. Allega gli output rilevanti."),
        ("LIPE-04", "Controllo risultato elaborazione", "Controlla il risultato dell'elaborazione e confrontalo con i dati disponibili. Registra rilievi ed evidenze."),
        ("LIPE-05", "Predisposizione invio", "Predisponi il materiale necessario all'invio e verifica che il fascicolo contenga gli elementi richiesti."),
        ("LIPE-06", "Verifica esito / ricevuta", "Verifica l'esito dell'invio e acquisisci la ricevuta o altra evidenza disponibile."),
        ("LIPE-07", "Completamento operativo", "Verifica che le attività operative siano complete e che le evidenze necessarie siano presenti prima di dichiarare concluso il task."),
    ],
    "F24_MENSILE": [
        ("F24-01", "Raccolta debiti e crediti", "Raccogli debiti, crediti compensabili e deleghe necessarie per il periodo."),
        ("F24-02", "Verifica compensazioni", "Controlla capienza, limiti e correttezza delle compensazioni previste."),
        ("F24-03", "Predisposizione modello F24", "Predisponi il modello con codici tributo, periodi e importi corretti."),
        ("F24-04", "Controllo finale modello", "Esegui il controllo formale e sostanziale prima dell'invio."),
        ("F24-05", "Invio e acquisizione ricevuta", "Esegui l'invio e acquisisci la ricevuta nel fascicolo della pratica."),
    ],
    "RICONC_BANCA": [
        ("RB-01", "Acquisizione movimenti bancari", "Acquisisci estratti conto e movimenti del periodo."),
        ("RB-02", "Abbinamento movimenti", "Abbina i movimenti bancari alle registrazioni contabili disponibili."),
        ("RB-03", "Analisi differenze", "Individua e documenta le differenze ancora aperte."),
        ("RB-04", "Registrazioni di rettifica", "Predisponi o verifica le registrazioni necessarie alla riconciliazione."),
        ("RB-05", "Chiusura riconciliazione", "Verifica che saldo contabile e saldo banca siano riconciliati e documentati."),
    ],
    "CU_ANNUALE": [
        ("CU-01", "Raccolta dati percipienti", "Verifica anagrafiche, compensi e ritenute dei percipienti."),
        ("CU-02", "Controllo quadrature", "Controlla quadrature tra contabilità, versamenti e dati delle certificazioni."),
        ("CU-03", "Elaborazione CU", "Genera le certificazioni e verifica gli elementi obbligatori."),
        ("CU-04", "Controllo certificazioni", "Controlla a campione e sulle anomalie le certificazioni prodotte."),
        ("CU-05", "Invio telematico", "Predisponi ed esegui l'invio telematico."),
        ("CU-06", "Acquisizione ricevute", "Acquisisci ricevute ed eventuali scarti nel fascicolo."),
    ],
    "BILANCIO_VER": [
        ("BIL-01", "Verifica saldi contabili", "Verifica saldi e quadrature preliminari del periodo."),
        ("BIL-02", "Scritture di assestamento", "Predisponi e verifica ratei, risconti, ammortamenti e altre scritture di assestamento."),
        ("BIL-03", "Controllo mastrini e partitari", "Analizza mastrini e partitari rilevanti e documenta le anomalie."),
        ("BIL-04", "Predisposizione prospetti", "Predisponi i prospetti di bilancio e le riconciliazioni di supporto."),
        ("BIL-05", "Controllo finale", "Esegui il controllo finale dei prospetti e delle evidenze raccolte."),
        ("BIL-06", "Fascicolo di chiusura", "Completa il fascicolo con documenti, note e verifiche conclusive."),
    ],
}


def build_tasks(practice_type_code: str) -> list[Task]:
    return [
        Task(code=code, title=title, instructions=instructions)
        for code, title, instructions in PRACTICE_TEMPLATES[practice_type_code]
    ]


def build_lipe_trim_tasks() -> list[Task]:
    return build_tasks("LIPE_TRIM")
