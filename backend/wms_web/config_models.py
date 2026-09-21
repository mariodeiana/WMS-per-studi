"""Validation and instantiation of editable practice models."""
import math
from datetime import date, timedelta
from uuid import uuid4
from backend.wms_core.models import Practice, Task


def validate_model(model, groups):
    tasks = model.setdefault("tasks", [])
    if not isinstance(tasks, list) or len(tasks) > 200:
        raise ValueError("Il modello deve contenere al massimo 200 attività")
    model["requires_validation"] = bool(model.get("requires_validation", True))
    codes = set()
    for task in tasks:
        if not isinstance(task, dict): raise ValueError("Attività non valida")
        for field in ("code", "title", "assigned_group"):
            if not isinstance(task.get(field), str) or not task[field].strip():
                raise ValueError("Ogni attività richiede codice, titolo e gruppo responsabile")
            task[field] = task[field].strip()
        if task["code"] == "@END": raise ValueError("@END è riservato alla fine del percorso")
        if task["code"] in codes: raise ValueError("Codici attività duplicati")
        codes.add(task["code"])
        if not any(g["id"] == task["assigned_group"] and g["role"] == "OPERATORE" for g in groups):
            raise ValueError("Le attività devono essere assegnate a un gruppo operatore esistente")
        days = task.get("days_before_due", 0)
        if isinstance(days, bool) or not isinstance(days, int) or not 0 <= days <= 3650:
            raise ValueError("L'anticipo della scadenza deve essere un intero tra 0 e 3650 giorni")
        task["days_before_due"] = days
        position = task.get("graph_position")
        if position is not None:
            if not isinstance(position, dict) or set(position) != {"x", "y"} or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 100000
                for v in position.values()
            ): raise ValueError("Posizione del nodo non valida")
        task["required"] = bool(task.get("required", True))

        # Dipendenze legacy: mantenute durante la migrazione.
        deps = task.setdefault("depends_on", [])
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            raise ValueError("Dipendenze non valide")

        if deps:
            raise ValueError("Sostituire i prerequisiti con transizioni in avanti")

        # Workflow: esiti selezionabili al completamento dell'attività.
        outcomes = task.setdefault("outcomes", [])
        if not isinstance(outcomes, list) or not all(isinstance(o, str) and o.strip() for o in outcomes):
            raise ValueError("Esiti attività non validi")
        outcomes[:] = [o.strip() for o in outcomes]
        if len(outcomes) != len(set(outcomes)):
            raise ValueError(f"Esiti duplicati nell'attività {task['code']}")

        # Workflow: esito -> una o più attività successive.
        transitions = task.setdefault("transitions", {})
        if not isinstance(transitions, dict):
            raise ValueError("Transizioni attività non valide")
        for outcome, destinations in transitions.items():
            if outcome != "*" and outcome not in outcomes:
                raise ValueError(f"Transizione con esito non configurato nell'attività {task['code']}: {outcome}")
            if not isinstance(destinations, list) or not all(isinstance(d, str) and d.strip() for d in destinations):
                raise ValueError(f"Destinazioni non valide per l'esito {outcome}")
            transitions[outcome] = [d.strip() for d in destinations]

    # Verifica che tutte le destinazioni delle transizioni esistano.
    for task in tasks:
        for outcome, destinations in task["transitions"].items():
            for destination in destinations:
                if destination != "@END" and destination not in codes:
                    raise ValueError(
                        f"Transizione {task['code']} / {outcome} verso attività inesistente: {destination}"
                    )

    # Il grafo minimo è aciclico: ciascun nodo viene eseguito una sola volta.
    graph = {t["code"]: {d for ds in t["transitions"].values() for d in ds if d != "@END"} for t in tasks}
    visiting, visited = set(), set()
    def visit(code):
        if code in visiting: raise ValueError("Le transizioni delle attività formano un ciclo")
        if code in visited: return
        visiting.add(code)
        for destination in graph[code]: visit(destination)
        visiting.remove(code)
        visited.add(code)
    for code in graph: visit(code)
    model_graph_issues(tasks)


def model_graph_issues(tasks):
    incoming = {d for t in tasks for ds in t.get("transitions", {}).values() for d in ds}
    legacy = not any("is_initial" in t for t in tasks)
    for t in tasks:
        if legacy: t["is_initial"] = t["code"] not in incoming
        else: t.setdefault("is_initial", False)
        if not isinstance(t["is_initial"], bool): raise ValueError("Nodo iniziale deve essere vero o falso")
    reached, pending = set(), [t["code"] for t in tasks if t["is_initial"]]
    graph = {t["code"]: t for t in tasks}
    while pending:
        code = pending.pop()
        if code in reached or code not in graph: continue
        reached.add(code)
        pending.extend(d for ds in graph[code].get("transitions", {}).values() for d in ds)
    issues = []
    if tasks and not any(t["is_initial"] for t in tasks): issues.append("Nessun nodo iniziale")
    for t in tasks:
        if t["code"] not in reached:
            reason = "senza ingressi e non iniziale" if t["code"] not in incoming else "non raggiungibile da un nodo iniziale"
            issues.append(f"{t['code']}: {reason}")
    return issues


def create_configured_practice(service, config, body, principal, *, origin="MANUALE", persist=True):
    if principal["role"] != "AMMINISTRATORE":
        raise PermissionError("Solo un amministratore può creare pratiche dalla configurazione")
    with config._lock, service._lock:
        client = next((c for c in config.list("clients") if c["id"] == body.get("client_id") and c.get("active", True)), None)
        model = next((m for m in config.list("practice_types") if m["id"] == body.get("model_id") and m.get("active", True)), None)
        if client is None: raise ValueError("Selezionare un cliente attivo")
        if model is None: raise ValueError("Selezionare un modello attivo")
        if origin not in {"MANUALE", "AUTOMATICA"}: raise ValueError("Origine non valida")
        included = model["id"] in client.get("repertoire", [])
        if origin == "AUTOMATICA" and not included:
            raise ValueError("Generazione automatica consentita solo per tipi pratica in repertorio")
        validate_model(model, config.list("groups"))
        if not model["tasks"]: raise ValueError("Aggiungere almeno un'attività al modello prima di creare una pratica")
        issues = model_graph_issues(model["tasks"])
        if issues: raise ValueError("Correggere il grafo prima di creare la pratica: " + "; ".join(issues))
        active_groups = {g["id"] for g in config.list("groups") if g.get("active", True)}
        if any(t["assigned_group"] not in active_groups for t in model["tasks"]):
            raise ValueError("Il modello usa un gruppo disattivato")
        try:
            start, end, due = [date.fromisoformat(str(body.get(k, ""))) for k in ("period_start", "period_end", "due_date")]
        except ValueError as error: raise ValueError("Inserire date valide per periodo e scadenza") from error
        if end < start: raise ValueError("La fine del periodo precede l'inizio")
        tasks = [
            Task(
                code=t["code"],
                title=t["title"],
                instructions=t.get("instructions", ""),
                required=t["required"],
                assigned_group=t["assigned_group"],
                depends_on=tuple(t["depends_on"]),
                outcomes=tuple(t["outcomes"]),
                transitions={
                    outcome: tuple(destinations)
                    for outcome, destinations in t["transitions"].items()
                },
                graph_position=dict(t["graph_position"]) if t.get("graph_position") else None,
                active=t["is_initial"],
            )
            for t in model["tasks"]
        ]
        for task, spec in zip(tasks, model["tasks"]):
            try: task.due_date = (due - timedelta(days=spec["days_before_due"])).isoformat()
            except OverflowError as error: raise ValueError("Scadenza attività fuori intervallo") from error
        practice = Practice(id="P-" + uuid4().hex[:12].upper(), practice_type_code=model["code"], client_id=client["id"], period_start=start.isoformat(), period_end=end.isoformat(), due_date=due.isoformat(), requires_validation=model["requires_validation"], tasks=tasks)
        practice.practice_type_id = model["id"]
        practice.origin = origin
        practice.economic_regime = "IN_REPERTORIO" if included else "EXTRA_CONTRATTO"
        practice.record("PRACTICE_CREATED", principal["username"], model_id=model["id"], client_id=client["id"], origin=practice.origin, economic_regime=practice.economic_regime)
        service._practices[practice.id] = practice
        try:
            if persist: service._persist()
        except Exception:
            del service._practices[practice.id]
            raise
        return service.get_for(practice.id, principal)


def generate_repertoire_practices(service, config, body, principal):
    """Generate one type/period for active subscribers, atomically and idempotently."""
    if principal['role'] != 'AMMINISTRATORE':
        raise PermissionError('Generazione riservata agli amministratori')
    with config._lock, service._lock:
        model = next((m for m in config.list('practice_types') if m['id'] == body.get('model_id') and m.get('active', True)), None)
        if model is None: raise ValueError('Selezionare un modello attivo')
        # Validate even when no clients subscribe.
        validate_model(model, config.list('groups'))
        if not model['tasks']: raise ValueError('Il modello non contiene attività')
        try:
            start, end, due = [date.fromisoformat(str(body.get(k, ''))) for k in ('period_start', 'period_end', 'due_date')]
        except ValueError as error: raise ValueError('Inserire date valide') from error
        if end < start: raise ValueError('La fine del periodo precede l’inizio')
        before = dict(service._practices)
        generated = []
        try:
            for client in config.list('clients'):
                if not client.get('active', True) or model['id'] not in client.get('repertoire', []): continue
                if any(p.origin == 'AUTOMATICA' and p.practice_type_id == model['id'] and p.client_id == client['id'] and p.period_start == start.isoformat() and p.period_end == end.isoformat() for p in service._practices.values()): continue
                generated.append(create_configured_practice(service, config, {**body, 'client_id': client['id']}, principal, origin='AUTOMATICA', persist=False))
            if generated: service._persist()
        except Exception:
            service._practices = before
            raise
        return generated
